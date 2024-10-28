import numpy as np
import matplotlib.pylab as plt

from scipy.stats import truncnorm

from src.data.spectrum_decomposition.spectrum import SpectrumDecomposition
from src.data.utils import SPECTRUMS


class NoiseMachine:
    @classmethod
    def point_anomaly(cls, data, num, std=1.0):
        """
        Introduce point anomalies into the data.

        :param data: pandas DataFrame
        :param num: int, number of anomalies to introduce
        :param std: float, standard deviation of the noise
        :return: pandas DataFrame with added point anomalies
        """
        data = cls._init_noise(data)
        noise = np.random.normal(0.0, std, num)
        index = np.random.randint(0, len(data), num)
        data.loc[index, "noise"] = noise
        data.loc[index, "noise_type"] = "point_anomaly"
        return data

    @classmethod
    def gaussian_anomaly(cls, data, std=0.1):
        """
        Introduce Gaussian noise into the data.

        :param data: pandas DataFrame
        :param std: float, standard deviation of the Gaussian noise
        :return: pandas DataFrame with added Gaussian noise
        """
        data = cls._init_noise(data)
        noise = np.random.normal(0.0, std, len(data))
        data["noise"] = noise
        data["noise_type"] = "gaussian_anomaly"
        return data

    @classmethod
    def shift_anomaly(
        cls, data, column="torqueactual", start=0, length=0, strength=1.0
    ):
        """
        param data: pandas DataFrame
        param start: int, start index of the data
        param length: int, data points affected
        param column: str, column name of the data
        param strength: float, strength of the shift in std.
        """
        data = cls._init_noise(data)

        end = start + length
        if not end:
            end = len(data)

        std = data[column].values[start:end].std()
        shift = np.random.normal(0.0, strength * std)
        data.loc[start:end, "noise"] = shift
        data.loc[start:end, "noise_type"] = "shift_anomaly"
        return data

    @classmethod
    def trend_anomaly(cls, data, max_shift=0.1):
        """
        Introduce a trend anomaly into the data.

        :param data: pandas DataFrame
        :param max_shift: float, maximum shift over the length of the data
        :return: pandas DataFrame with added trend anomaly
        """
        data = cls._init_noise(data)
        slope = max_shift / len(data)
        shift = np.arange(0, max_shift, slope)
        data["noise"] = shift
        data["noise_type"] = "trend_anomaly"
        return data

    @classmethod
    def sinusoidal_anomaly(cls, data, anom_len, amplitude=1.0, mirror=True):
        """
        Introduce a sinusoidal anomaly (rail misalignment) into the data.

        :param data: pandas DataFrame
        :param anom_len: int, length of the anomaly
        :param amplitude: float, amplitude of the sinusoidal wave
        :param mirror: bool, whether to mirror the anomaly
        :return: pandas DataFrame with added sinusoidal anomaly
        """
        data = cls._init_noise(data)

        m_idpoint = int(len(data) / 2)
        a = m_idpoint - anom_len

        start_idx = np.random.randint(0, a)
        end_idx = start_idx + anom_len

        t = np.linspace(0, np.pi, anom_len)
        sinusoidal_pattern = np.sin(t*2/3*np.pi) * amplitude

        data.loc[start_idx : end_idx - 1, "noise"] = sinusoidal_pattern

        if mirror:
            neg_pattern = sinusoidal_pattern * -1
            mirror_start_idx = len(data) - end_idx
            mirror_end_idx = len(data) - start_idx

            data.loc[mirror_start_idx : mirror_end_idx - 1, "noise"] = neg_pattern

        data["noise_type"] = "sinusoidal"
        return data

    @staticmethod
    def _init_noise(data):
        """
        Initialize the noise columns in the DataFrame.

        :param data: pandas DataFrame
        :return: pandas DataFrame with initialized noise columns
        """
        data = data.reset_index(drop=True)
        if "noise" not in data.columns:
            data["noise"] = 0.0
            data["noise_type"] = ""
        return data

    @classmethod
    def plot(cls, data, column="torqueactual", params="{}"):
        """
        Plot the original and noisy data.

        :param data: pandas DataFrame
        :param column: str, column to plot
        """
        noise = data[data["noise"] != 0]
        noise_type = noise["noise_type"].values[0]
        x = data["timeindex"]

        fig, ax = plt.subplots(figsize=(15, 7))
        if noise_type == "point_anomaly":
            ax.scatter(
                noise["timeindex"],
                noise[column] + noise["noise"],
                label="anomaly",
                c="r",
                marker="x",
            )
        elif noise_type == "trend_anomaly":
            data[f"{column}_noise"] = data[column] + data["noise"]
            data_group = (
                data[["id", column, f"{column}_noise"]]
                .groupby("id")
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
                noise[column] + noise["noise"],
                label="anomaly",
                c="r",
            )
        ax.plot(x, data[column], label="original", alpha=0.7)
        ax.set_title(f"{noise_type} -- {column} -- params {params}")
        ax.legend()
        fig.show()


class NoiseFactory:
    def __init__(self, data):
        self.data = data
        self.samples = data["id"].unique()
        self.min_sample_length = (
            data[data["id"].isin(self.samples)]["id"].value_counts().min()
        )
        self.decomposer = SpectrumDecomposition()

    def gen_point_anomalies(self):
        stds = np.geomspace(1, 10, 5)
        min_n, max_n = 5, 10
        for std in stds:
            for n in range(min_n, max_n):
                for _id in self.samples:
                    sample = self.data[self.data["id"] == _id]
                    sample_noise = NoiseMachine.point_anomaly(sample, n, std)
                    sample_noise["torqueactual"] += sample_noise["noise"]
                    sample_noise_decomposed = self.decomposer.transform(
                        sample_noise, freq=SPECTRUMS
                    )
                    yield _id, sample_noise_decomposed, std, n

    def gen_gaussian_anomalies(self):
        stds = np.geomspace(0.01, 0.1, 5)
        for std in stds:
            for _id in self.samples:
                sample = self.data[self.data["id"] == _id]
                sample_noise = NoiseMachine.gaussian_anomaly(sample, std)
                sample_noise["torqueactual"] = (
                    sample_noise["torqueactual"] + sample_noise["noise"]
                )
                sample_noise_decomposed = self.decomposer.transform(
                    sample_noise, freq=SPECTRUMS
                )
                yield _id, sample_noise_decomposed, std

    def gen_shift_anomaly(self):
        starts = np.random.randint(200, self.min_sample_length, 5)
        lengths = np.geomspace(150, 1500, 5, dtype=int)
        strengths = np.geomspace(1.0, 10.0, 5)

        for start in starts:
            for length in lengths:
                for strength in strengths:
                    for _id in self.samples:
                        sample = self.data[self.data["id"] == _id]
                        sample_noise = NoiseMachine.shift_anomaly(
                            sample, start=start, length=length, strength=strength
                        )
                        sample_noise["torqueactual"] += sample_noise["noise"]
                        sample_noise_decomposed = self.decomposer.transform(
                            sample_noise, freq=SPECTRUMS
                        )
                        yield (
                            _id,
                            sample_noise_decomposed,
                            int(start),
                            int(length),
                            strength,
                        )

    def gen_trend_anomaly(self):
        max_shifts = np.geomspace(0.1, 10, 5)

        for shift in max_shifts:
            for _id in self.samples:
                sample = self.data[self.data["id"] == _id]
                sample_noise = NoiseMachine.trend_anomaly(sample, max_shift=shift)
                sample_noise["torqueactual"] += sample_noise["noise"]
                sample_noise_decomposed = self.decomposer.transform(
                    sample_noise, freq=SPECTRUMS
                )
                yield _id, sample_noise_decomposed, shift

    def gen_sinusoidal_anomaly(self):
        lengths = np.geomspace(150, self.min_sample_length / 2.5, 5, dtype=int)
        amplitudes = np.geomspace(1, 5, 5)

        for length in lengths:
            for amplitude in amplitudes:
                for _id in self.samples:
                    sample = self.data[self.data["id"] == _id]
                    sample_noise = NoiseMachine.sinusoidal_anomaly(
                        sample, anom_len=length, amplitude=amplitude
                    )
                    sample_noise["torqueactual"] += sample_noise["noise"]
                    sample_noise_decomposed = self.decomposer.transform(
                        sample_noise, freq=SPECTRUMS
                    )
                    yield _id, sample_noise_decomposed, int(length), amplitude
