import numpy as np
import matplotlib.pylab as plt
import pandas as pd

from scipy.stats import truncnorm
from functools import partial

class NoiseFactory:
    @classmethod
    def generate(cls, df, columns, ratio, machine):
        num_samples = round(len(df['seqid'].unique()) * ratio)
        ids = np.random.choice(df['seqid'].unique(), num_samples)

        df_selected = df[df['seqid'].isin(ids)]
        df_synthetic = df_selected.groupby('seqid').apply(machine).reset_index(drop=True)

        df_original = df.groupby('seqid').apply(NoiseMachine.no_anomaly).reset_index(drop=True)

        return pd.concat([df_original, df_synthetic])

    @classmethod
    def gaussian(cls, df, columns, ratio, stdtimes):
        machine = partial(NoiseMachine.gaussian_anomaly, stdtimes=stdtimes)   
        return cls.generate(df, columns, ratio, machine)
    
    @classmethod
    def sinusoidal(cls, df, columns, ratio, amplitude, length=0.2):
        machine = partial(NoiseMachine.sinusoidal_anomaly, anomlength=length, amplitude=amplitude)   
        return cls.generate(df, columns, ratio, machine)
    
    @classmethod
    def point(cls, df, columns, ratio, stdtimes, amount=4):
        machine = partial(NoiseMachine.point_anomaly, num=amount, stdtimes=stdtimes)   
        return cls.generate(df, columns, ratio, machine)


class NoiseMachine:
    @classmethod
    def no_anomaly(cls, data):
        result = cls._init_noise(data)
        result['seqid'] = result['seqid'] + "|original"
        return cls._init_noise(data)

    @classmethod
    def point_anomaly(cls, data, num, stdtimes=1.0, minstd=1.5, mirror=False, replacetorque=True):
        """
        Introduce point anomalies into the data.

        :param data: pandas DataFrame
        :param num: int, number of anomalies to introduce
        :param std: float, standard deviation of the noise
        :return: pandas DataFrame with added point anomalies
        """
        data = cls._init_noise(data)
        std = data['torqueactual'].std()

        noise = truncnorm.rvs(minstd/std, np.inf, size=num, scale=std*stdtimes)
        index = data.sample(num).index

        data.loc[index, "anomaly_syn"] = noise
        data.loc[index, "anomaly_syn_type"] = "point"

        if replacetorque:
            data['torqueactual'] += data['anomaly_syn']

        data['seqid'] = data['seqid'] + "|point"

        return data
    
    @classmethod
    def sinusoidal_anomaly(cls, data, anomlength, amplitude=0.5, mirror=True, replacetorque=True):
        """
        Introduce a sinusoidal anomaly (rail misalignment) into the data.

        :param data: pandas DataFrame
        :param anom_len: int, length of the anomaly
        :param amplitude: float, amplitude of the sinusoidal wave
        :param mirror: bool, whether to mirror the anomaly
        :return: pandas DataFrame with added sinusoidal anomaly
        """
        data = cls._init_noise(data)
        std = data['torqueactual'].std()
        anom_len = round(len(data)/2 * anomlength)

        index_min = data.index.min()
        index_max = data.index.max()

        m_idpoint = int(len(data) / 2)
        a = m_idpoint - anom_len

        start_idx = np.random.randint(0, a) + index_min
        end_idx = start_idx + anom_len

        t = np.linspace(0, np.pi/2, anom_len)
        sinusoidal_pattern = np.sin(t*2/3*np.pi) * amplitude * std * np.random.choice([-1, 1])

        data.loc[start_idx : end_idx - 1, "anomaly_syn"] = sinusoidal_pattern

        if mirror:
            neg_pattern = sinusoidal_pattern * -1
            mirror_start_idx =  index_max - end_idx + index_min
            mirror_end_idx = index_max - start_idx + index_min

            data.loc[mirror_start_idx : mirror_end_idx - 1, "anomaly_syn"] = neg_pattern

        data["anomaly_syn_type"] = "sinusoidal"
        if replacetorque:
            data['torqueactual'] += data['anomaly_syn']

        data['seqid'] = data['seqid'] + "|sinus"

        return data

    @classmethod
    def gaussian_anomaly(cls, data, stdtimes=0.25, replacetorque=True):
        """
        Introduce Gaussian noise into the data.

        :param data: pandas DataFrame
        :param std: float, standard deviation of the Gaussian noise
        :return: pandas DataFrame with added Gaussian noise
        """
        data = cls._init_noise(data)
        std = data['torqueactual'].std()

        noise = np.random.normal(0.0, std*stdtimes, len(data))

        data["anomaly_syn"] = noise
        data["anomaly_syn_type"] = "gaussian"        
        if replacetorque:
            data['torqueactual'] += data['anomaly_syn']

        data['seqid'] = data['seqid'] + "|gaussian"

        return data
    
    @classmethod
    def generate_anomalies(cls, data : pd.DataFrame):
        results = []

        results += [NoiseMachine.gaussian_anomaly(data.copy())]
        results[-1]['seqid'] = results[-1]['seqid'] + "|anom_gaussian"

        results += [NoiseMachine.point_anomaly(data.copy(), np.random.choice(range(3,7)))]
        results[-1]['seqid'] = results[-1]['seqid'] + "|anom_point"


        results += [NoiseMachine.sinusoidal_anomaly(data.copy(), np.random.uniform(0.02, 0.2))]
        results[-1]['seqid'] = results[-1]['seqid'] + "|anom_sinus"

        return pd.concat(results)



    @staticmethod
    def _init_noise(data):
        """
        Initialize the noise columns in the DataFrame.

        :param data: pandas DataFrame
        :return: pandas DataFrame with initialized noise columns
        """
        data["anomaly_syn"] = 0.0
        data["anomaly_syn_type"] = ""

        return data

    @classmethod
    def plot(cls, data, column="torqueactual", params="{}"):
        """
        Plot the original and noisy data.

        :param data: pandas DataFrame
        :param column: str, column to plot
        """
        noise = data[data["anomaly_syn"] != 0]
        noise_type = noise["anomaly_syn_type"].values[0]
        x = data["timeindex"]

        fig, ax = plt.subplots(figsize=(15, 7))
        if noise_type == "point":
            ax.scatter(
                noise["timeindex"],
                noise["torqueactual"],
                label="anomalies",
                c="r",
                marker="x", # type: ignore
            )
        elif noise_type == "trend_anomaly":
            data[f"{column}_noise"] = data[column] + data["anomaly_syn"]
            data_group = (
                data[["seqid", column, f"{column}_noise"]]
                .groupby("seqid")
                .agg("mean")
                .reset_index()
            )
            ax.plot(data_group.index, data_group[column], label="original")
            ax.plot(
                data_group.index, data_group[f"{column}_noise"], label="anomaly", c="r"
            )
            ax.set_title(f"{noise_type} -- {column} mean per sequence -- params {params}")
            ax.legend()
            fig.show()
            return
        else:
            ax.plot(
                noise["timeindex"],
                noise["torqueactual"],
                label="anomalies",
                c="r",
            )
        ax.plot(x, data[column]-data['anomaly_syn'], label="Torque", alpha=0.7)
        ax.set_title(f"{noise_type} -- {column} -- params {params}")
        ax.legend()
        fig.show()

    @classmethod
    def _plot(cls, data, ax, column="torqueactual", params="{}"):
        """
        Plot the original and noisy data.

        :param data: pandas DataFrame
        :param column: str, column to plot
        """
        noise = data[data["anomaly_syn"] != 0]
        noise_type = noise["anomaly_syn_type"].values[0]
        x = data["timeindex"]

        if noise_type == "point":
            ax.scatter(
                noise["timeindex"],
                noise["torqueactual"],
                label="anomalies",
                c="r",
                marker="x", # type: ignore
            )
        elif noise_type == "trend_anomaly":
            data[f"{column}_noise"] = data[column] + data["anomaly_syn"]
            data_group = (
                data[["seqid", column, f"{column}_noise"]]
                .groupby("seqid")
                .agg("mean")
                .reset_index()
            )
            ax.plot(data_group.index, data_group[column], label="original")
            ax.plot(
                data_group.index, data_group[f"{column}_noise"], label="anomaly", c="r"
            )
            ax.set_title(f"{noise_type} -- {column} mean per sequence -- params {params}")
            return
        else:
            ax.plot(
                noise["timeindex"],
                noise["torqueactual"],
                label="anomalies",
                c="r",
            )
        ax.plot(x, data[column]-data['anomaly_syn'], label="Torque", alpha=0.7)
        ax.set_title(f"{noise_type} -- {column} -- params {params}")


# class NoiseFactory:
#     def __init__(self, data):
#         self.data = data
#         self.samples = data["seqid"].unique()
#         self.min_sample_length = (
#             data[data["seqid"].isin(self.samples)]["seqid"].value_counts().min()
#         )
#         self.decomposer = SpectrumDecomposition()

#     def gen_point_anomalies(self):
#         stds = np.geomspace(1, 10, 5)
#         min_n, max_n = 5, 10
#         for std in stds:
#             for n in range(min_n, max_n):
#                 for _id in self.samples:
#                     sample = self.data[self.data["seqid"] == _id]
#                     sample_noise = NoiseMachine.point_anomaly(sample, n, std)
#                     sample_noise["torqueactual"] += sample_noise["anomaly_syn"]
#                     sample_noise_decomposed = self.decomposer.transform(
#                         sample_noise, freq=g.decomposition_spectrums
#                     )
#                     yield _id, sample_noise_decomposed, std, n

#     def gen_sinusoidal_anomaly(self):
#         lengths = np.geomspace(150, self.min_sample_length / 2.5, 5, dtype=int)
#         amplitudes = np.geomspace(1, 5, 5)

#         for length in lengths:
#             for amplitude in amplitudes:
#                 for _id in self.samples:
#                     sample = self.data[self.data["seqid"] == _id]
#                     sample_noise = NoiseMachine.sinusoidal_anomaly(
#                         sample, anom_len=length, amplitude=amplitude
#                     )
#                     sample_noise["torqueactual"] += sample_noise["anomaly_syn"]
#                     sample_noise_decomposed = self.decomposer.transform(
#                         sample_noise, freq=g.decomposition_spectrums
#                     )
#                     yield _id, sample_noise_decomposed, int(length), amplitude

#     def gen_gaussian_anomalies(self):
#         stds = np.geomspace(0.01, 0.1, 5)
#         for std in stds:
#             for _id in self.samples:
#                 sample = self.data[self.data["seqid"] == _id]
#                 sample_noise = NoiseMachine.gaussian_anomaly(sample, std)
#                 sample_noise["torqueactual"] = (
#                     sample_noise["torqueactual"] + sample_noise["anomaly_syn"]
#                 )
#                 sample_noise_decomposed = self.decomposer.transform(
#                     sample_noise, freq=g.decomposition_spectrums
#                 )
#                 yield _id, sample_noise_decomposed, std
