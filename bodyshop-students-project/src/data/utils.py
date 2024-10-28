import matplotlib.pyplot as plt
import random
import pandas as pd
import sys
import os

current_dir = os.path.dirname(os.path.realpath(__file__))
rootdir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))



SPECTRUMS = [
    [0.0, 3000.0],
    [3050.0, 6050.0],
    [6100.0, 9100.0],
    [9150.0, 12150.0],
    [12200.0, 15200.0],
    [15250.0, 18250.0],
]


def add_type_column(df):
    df["type"] = df["id"].apply(lambda x: x.split("-")[1].split("|")[0])
    df = add_robot_columns(df)
    return df


def load_dataset(id, cleaned=True): # ids are numbers starting from 0
    if type(id) != int:
        if cleaned:
            folder = "cleaned_data"
        else:
            folder = "raw_data"
        file_path = rootdir + "\\data\\" + folder + "\\" + id
        df = pd.read_parquet(file_path)
        if not (cleaned):
            df = add_robot_columns(df)
        print("Loaded dataset: " + folder + "\\" + id)
        return df
    
    path = rootdir + '\data'
    cleaned_datasets = [
        "\\cleaned_data\\additional_data_cleaned.parquet",          #0
        "\\cleaned_data\\Ta_type_cleaned.parquet",                  #1 comes from TrackDataset.snappy.parquet
        "\\cleaned_data\\TL_type_cleaned.parquet",                  #2 comes from TrackDataset.snappy.parquet
        "\\cleaned_data\\TL_type_additional_data_cleaned.parquet",  #3 comes from additional_data.parquet 
        "\\cleaned_data\\Ta_type_additional_data_cleaned.parquet",  #4 comes from additional_data.parquet
        "\\cleaned_data\\TL_all_data_without_duplicates.parquet",   #5 Merges all TL data and removes duplicates
        "\\cleaned_data\\interpolated_TL.parquet",                  #6 All TL data interpolated (without duplicates)
        "\\cleaned_data\\no_duplicates_freqs.parquet",              #7 All TL data interpolated (without duplicates) in the frequency domain.   
        ]

    raw_datasets = [
        "\\raw_data\\additional_data.parquet",
        "\\raw_data\\TrackDataset.snappy.parquet",
    ]

    # Choose the dataset to load
    file = cleaned_datasets[id] if cleaned else raw_datasets[id]
    file_path = path + file
    df = pd.read_parquet(file_path)
    if not (cleaned):
        df = add_robot_columns(df)
    print("Loaded dataset: " + file)
    return df

def add_robot_columns(df):
    df["robot_type"] = df["id"].apply(lambda x: x.split("-")[0])
    df["robot"] = df['robot_type'] + '-' + df["id"].apply(lambda x: x.split("-")[1].split("|")[0])
    return df


def plot_graph(df, id, series_type, y_axis1, y_axis2='', with_points=False):
    df_subset = df.where(df['id'] == id)
    try:
        df_subset = df_subset.where(df_subset['type'] == series_type)
    except KeyError:
        print("No type column in the dataset. Assuming is type TL.")
    if y_axis2 == '':
        if with_points:
            plt.plot(df_subset['timeindex'], df_subset[y_axis1], 'o')
        else:
            plt.plot(df_subset['timeindex'], df_subset[y_axis1])
        title = str(series_type) + '_' + y_axis1 + '_' + str(id)
        y_label = y_axis1
        plt.title(title)
        plt.xlabel("timeindex")
        plt.ylabel(y_label)
    else:
        fig, axs = plt.subplots(2)
        if with_points:
            axs[0].plot(df_subset['timeindex'], df_subset[y_axis1], 'o')
            axs[0].set_ylabel(y_axis1)
            axs[1].plot(df_subset['timeindex'], df_subset[y_axis2], 'o')
            axs[1].set_ylabel(y_axis2)
            axs[1].set_xlabel('timeindex')
        else:
            axs[0].plot(df_subset['timeindex'], df_subset[y_axis1])
            axs[0].set_ylabel(y_axis1)
            axs[1].plot(df_subset['timeindex'], df_subset[y_axis2])
            axs[1].set_ylabel(y_axis2)
            axs[1].set_xlabel('timeindex')
        plt.tight_layout()
        title = str(series_type) + "_" + y_axis1 + "/" + y_axis2 + "_" + str(id)
        axs[0].set_title(title)

    plt.show()


# changed the plot_graph function to work with preprocessed dfs from get_time_series
def plot_time_series(df, y_axis1, y_axis2):
    if y_axis2 == "":
        plt.plot(df["timeindex"], df[y_axis1], "o")
        title = y_axis1 + "_" + str(id)
        y_label = y_axis1
        plt.title(title)
        plt.xlabel("timeindex")
        plt.ylabel(y_label)
    else:
        fig, axs = plt.subplots(2)
        axs[0].plot(df["timeindex"], df[y_axis1], "o")
        axs[0].set_ylabel(y_axis1)
        axs[1].plot(df["timeindex"], df[y_axis2], "o")
        axs[1].set_ylabel(y_axis2)
        axs[1].set_xlabel("timeindex")
        plt.tight_layout()
        title = y_axis1 + "/" + y_axis2 + "_" + str(id)
        axs[0].set_title(title)

    plt.show()


# returns a dataframe with only one timeseries in it, identified via id
def get_time_series(base_df, index):
    ids = base_df["id"].unique()
    id = ids[index]
    df_temp = base_df[(base_df["id"] == id)]
    return df_temp


# removes the acceleration spikes from the beginning middle and end of the torque graph.
# window ratio determines how much of the data is removed (base = 2%)
def remove_spikes(df, window_ratio=0.02):
    window_size = int(len(df) * window_ratio)

    # Define indices for the three sections: beginning, middle, and end
    start_idx = 0
    mid_start_idx = len(df) // 2 - window_size
    mid_end_idx = mid_start_idx + window_size * 2
    end_idx = len(df) - window_size

    df_cleaned = pd.concat(
        [df.iloc[window_size:mid_start_idx], df.iloc[mid_end_idx:end_idx]]
    )

    return df_cleaned.reset_index(drop=True)


# a function to create a point anomaly in a timeseries. first use the get_time_series function.
# intensity should be a double (bigger than 1), and size an integer (how many successive points to modify)
def inject_point_anomaly(df, intensity, size):
    max_idx = len(df) - size
    slice_idx = random.randint(0, max_idx)
    end_idx = slice_idx + size

    df_slice = df[slice_idx:end_idx].copy()
    df_slice["torqueactual"] *= intensity

    df.iloc[slice_idx:end_idx] = df_slice

    return df


# works in principle the same as the function above, but you're gonna want to choose smaller intensity values
def inject_general_anomaly(df, intensity):
    df["torqueactual"] *= intensity
    return df

def get_root_dir():
    return rootdir
