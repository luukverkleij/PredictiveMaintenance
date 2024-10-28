import pandas as pd
from scipy.fft import rfft, rfftfreq, irfft
import numpy as np
import matplotlib.pyplot as plt

col_seqid = "seqid"
col_timeindex = "timeindex_bin"


class SpectrumDecomposition:
    def __init__(self, col_name="torqueactual", n_freq=25):
        self.col_name = col_name
        self.n_freq = n_freq
        # Frequency ranges in Fourier Transform
        self.freq_ranges = None

    def transform(self, data: pd.DataFrame, freq=None):
        """Decomposes a time series in frequency ranges using Fourier Transform"""
        self.max_length = int(data.groupby(col_seqid).size().max())

        # Find frequencies in Fourier Transform
        freq = (
            freq
            if freq
            else np.array_split(
                rfftfreq(self.max_length, d=2e-2 / self.max_length), self.n_freq
            )
        )

        decomposed_df = []
        for id in data[col_seqid].unique():
            # Fourier Transform
            sequence = data[data[col_seqid] == id]
            sequence = sequence.sort_values(col_timeindex)
            fourier = rfft(sequence[self.col_name].values)
            seq_freq = rfftfreq(len(sequence), d=2e-2 / self.max_length)

            freqs_signal = {}

            # Iterate for each frequency range for decomposition
            for spectrum in freq:
                fourier_filter = fourier.copy()
                min_freq, max_freq = np.min(spectrum), np.max(spectrum)

                # Remove (set to 0) frequencies outside the spectrum
                fourier_filter[(min_freq > seq_freq) | (max_freq < seq_freq)] = 0

                # Inverse Fourier Transform to get the signal in spectrum
                freqs_signal[f"{self.col_name}_{min_freq}_{max_freq}"] = irfft(
                    fourier_filter, n=len(sequence)
                )

            decomposed_sequence = pd.DataFrame.from_dict(freqs_signal)
            decomposed_sequence[self.col_name] = sequence[self.col_name].values
            decomposed_sequence[col_timeindex] = sequence[col_timeindex].values
            decomposed_sequence[col_seqid] = id

            # Inverse columns for visualization
            decomposed_sequence = decomposed_sequence[decomposed_sequence.columns[::-1]]
            decomposed_df.append(decomposed_sequence)

        self.freq_ranges = list(freqs_signal.keys())
        return pd.concat(decomposed_df)
    
    def time_to_freq(self, data: pd.DataFrame, abs: bool = True):
        """Transforms a time series into frequency domain"""
        transformed_data = pd.DataFrame()
        for id in data[col_seqid].unique():
            freqs_signal = pd.DataFrame()
            sequence = data[data[col_seqid] == id]
            sequence = sequence.sort_values(col_timeindex)
            fourier = rfft(sequence[self.col_name].values)
            seq_freq = rfftfreq(len(sequence), 0.01)
            freqs_signal[col_seqid] = None
            freqs_signal['freqs'] = seq_freq
            if abs:
                freqs_signal[self.col_name + '_abs'] = np.abs(fourier)
            else:
                freqs_signal[self.col_name + '_real'] = np.real(fourier)
                freqs_signal[self.col_name + '_imag'] = np.imag(fourier)
            freqs_signal[col_seqid] = id
            
            transformed_data = pd.concat([transformed_data, freqs_signal])

        return transformed_data

    def plot(self, sequence: pd.DataFrame):
        """Plots decomposed sequence, original and reconstructed signal"""
        sequence["reconstructed"] = sequence[self.freq_ranges].sum(axis=1)

        n_rows = 2 + (len(self.freq_ranges) // 2)
        fig, axes = plt.subplots(n_rows, 2, figsize=(20, 20))

        axes.flat[0].plot(sequence["torqueactual"])
        axes.flat[0].set_title("Original")
        axes.flat[1].plot(sequence["reconstructed"])
        axes.flat[1].set_title("Reconstructed")

        for i, col in enumerate(self.freq_ranges):
            axes.flat[i + 2].plot(sequence[col])
            axes.flat[i + 2].set_title(col)

        fig.tight_layout()
        plt.show()
