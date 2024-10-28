import pandas as pd

# Settings
data_folder_path = "data/tracks/"
experiments_folder_path = "experiments/"

# Databases paths
path_tracks_raw             = data_folder_path + "tracks.csv"
path_tracks                 = data_folder_path + "tracks.parquet"
path_tracks_up              = data_folder_path + 'tracks_ups.parquet'
path_tracks_fft             = data_folder_path + "tracks_fft.parquet"
path_tracks_results         = data_folder_path + "tracks_results.parquet"


path_tracks_syn             = data_folder_path + "tracks_syn.parquet"
path_tracks_syn_fft         = data_folder_path + "tracks_syn_fft.parquet"
path_tracks_syn_results     = data_folder_path + "tracks_syn_results.parquet"

path_series         = data_folder_path + "series.parquet"
path_series_results = data_folder_path + "series_results.parquet"

tracks_result_columns = ['seqid', 'robotid', 'date', 'time', 'timeindex_bin', 'timeindex', 'motorposition']

# Spectrums
decomposition_spectrums = [
    [0.0, 3000.0],
    [3050.0, 6050.0],
    [6100.0, 9100.0],
    [9150.0, 12150.0],
    [12200.0, 15200.0],
    [15250.0, 18250.0],
]

# Misc Constants
# robotid_experiment = ['6640-102140-1', '6640-101814-1']
robotid_experiment = ['6640-101814-1']
methods = ['z', 'mz', 'lof', 'if', 'hmm']


# Methods
def save_tracks_results(df, columns):
    df_out = pd.read_parquet(path_tracks_results)

    df_out = df_out.merge(df[['seqid', 'timeindex_bin'] + columns], on=['seqid', 'timeindex_bin'],  suffixes=('', '_drop'))
    df_out = df_out.drop([col for col in df_out.columns if col.endswith('_drop')], axis=1)

    df_out.to_parquet(path_tracks_results)

def save_tracks_synth_results(df, columns):
    df_out = pd.read_parquet(path_tracks_syn_results)

    df_out = df_out.merge(df[['seqid', 'timeindex_bin'] + columns], on=['seqid', 'timeindex_bin'],  suffixes=('', '_drop'))
    df_out = df_out.drop([col for col in df_out.columns if col.endswith('_drop')], axis=1)

    df_out.to_parquet(path_tracks_syn_results)