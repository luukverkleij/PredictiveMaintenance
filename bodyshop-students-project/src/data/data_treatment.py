import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import copy
import src.data.utils as utils

def label_direction(df, type_series):
    subset = df[df['type']==type_series]
    robots = df['robot'].unique()
    for robot in robots:
        # print(robot)
        ids = subset[subset['robot']==robot]['id'].unique()
        for id in ids:
            # print(id)
            id_subset = subset[subset['id']==id]
            # print(id_subset.head())
            first_value_time = id_subset.timeindex.iloc[0]
            # print(first_value_time)
            first_value = id_subset.loc[id_subset['timeindex'] == first_value_time, 'motorposition'].values[0]
            last_value_time = id_subset['timeindex'].iloc[-1]
            last_value = id_subset.loc[id_subset['timeindex'] == last_value_time, 'motorposition'].values[0]
            time_length = last_value_time - first_value_time
            middle_value_time = id_subset.loc[id_subset['timeindex'] > time_length/2, 'timeindex'].min()
            middle_value = id_subset.loc[id_subset['timeindex'] == middle_value_time, 'motorposition'].values[0]
            one_quarter_value_time = id_subset.loc[id_subset['timeindex'] > time_length/4, 'timeindex'].min()
            one_quarter_value = id_subset.loc[id_subset['timeindex'] == one_quarter_value_time, 'motorposition'].values[0]
            three_quarter_value_time = id_subset.loc[id_subset['timeindex'] > 3*time_length/4, 'timeindex'].min()
            three_quarter_value = id_subset.loc[id_subset['timeindex'] == three_quarter_value_time, 'motorposition'].values[0]
            torque_first_half_avg = id_subset.loc[id_subset['timeindex'] < time_length/2, 'torqueactual'].mean()
            if first_value < one_quarter_value and one_quarter_value < middle_value and middle_value > three_quarter_value and three_quarter_value > last_value:
                direction = 'up'
                subset.loc[subset['id']==id,'direction'] = direction
                if torque_first_half_avg > 0:
                    subset.loc[subset['id']==id,'same_direction'] = True
                else:
                    subset.loc[subset['id']==id,'same_direction'] = False
            elif first_value > one_quarter_value and one_quarter_value > middle_value and middle_value < three_quarter_value and three_quarter_value < last_value:
                direction = 'down'
                subset.loc[subset['id']==id,'direction'] = direction
                if torque_first_half_avg < 0:
                    subset.loc[subset['id']==id,'same_direction'] = True
                else:
                    subset.loc[subset['id']==id,'same_direction'] = False
            else:
                direction = 'unknown'
                subset.loc[subset['id']==id,'direction'] = direction
        directions = subset[subset['robot']==robot]['direction'].unique()
        same_directions = subset[subset['robot']==robot]['same_direction'].unique()
        print(robot, directions, same_directions)
    return subset

#Plot graph function

def make_direction_up(subset, flip_only_position = False): #For dataset add_data flip_only_position = False, for the dataset TrackDataset flip_only_position = True
    #Erasing series with unknown direction
    subset = subset[subset['direction']!='unknown']

    #Making all robots have the same direction and start at 0 (motorposition)

    down_ids = subset[subset['direction']=='down']['id'].unique()
    ids = subset['id'].unique()
    for id in ids:
        first_value = subset.loc[subset['id']==id,'motorposition'].iloc[0]
        same_direction = subset.loc[subset['id']==id,'same_direction'].iloc[0]
        if id in down_ids:
            subset.loc[subset['id']==id,'motorposition'] = first_value - subset.loc[subset['id']==id,'motorposition']
            if same_direction:
                subset.loc[subset['id']==id, 'speedsetpoint'] = -subset.loc[subset['id']==id, 'speedsetpoint']
                subset.loc[subset['id']==id, 'torqueactual'] = -subset.loc[subset['id']==id, 'torqueactual']
        else:
            if not same_direction:
                subset.loc[subset['id']==id, 'speedsetpoint'] = -subset.loc[subset['id']==id, 'speedsetpoint']
                subset.loc[subset['id']==id, 'torqueactual'] = -subset.loc[subset['id']==id, 'torqueactual']
            if first_value == 0:
                continue
            subset.loc[subset['id']==id,'motorposition'] = subset.loc[subset['id']==id,'motorposition'] - first_value
    return subset


#Check whether all series start at 0
def check_start_zero(new_df):
    ids = new_df['id'].unique()
    for id in ids:
        first_time = new_df.loc[new_df['id']==id,'timeindex'].min()
        first_value = new_df.loc[new_df['id']==id,'motorposition'].where(new_df['timeindex']==first_time).values[0]
        if first_value != 0:
            print(id, first_value)

def export_data(subset, filename, cleaned = True):
    import os
    rootdir = utils.get_root_dir()
    if cleaned:
        path = rootdir + '\\data\\cleaned_data'
    else:
        path = rootdir + '\\data\\raw_data'
    file_path = path + '\\' + filename
    # del subset['direction']
    subset.to_parquet(file_path, compression='snappy')
    print('Data exported to', file_path)

def get_unique_ids(df):
    df = df.sort_values(by=['id', 'timeindex'])

    initial_ids = df['id'].unique()
    print("Number of initial sequences:", initial_ids.size)

    # Step 2: Group by sequence_id and aggregate torque values as a tuple
    grouped = df.groupby('id')['torqueactual'].apply(tuple)

    # Step 3: Find unique sequences
    unique_sequences = grouped.drop_duplicates()

    unique_sequence_ids = unique_sequences.index.tolist()

    # Output the number of unique sequences
    num_unique_sequences = unique_sequences.size

    print("Number of unique sequences:", num_unique_sequences)

    return unique_sequence_ids

def drop_duplicates(df):
    unique_sequence_ids = get_unique_ids(df)
    df = df[df['id'].isin(unique_sequence_ids)]
    return df

def print_series_per_robot(df):
    robot_types = df['robot_type'].unique()
    distinct_robot_types = df.groupby(df['id'].str[:4])['id'].nunique()
    print(distinct_robot_types)
    for robot_type in robot_types:
        id_subset = df.where(df['robot_type'] == robot_type)
        distinct_robots = id_subset.groupby(id_subset['id'].str[:11])['id'].nunique()
        print(distinct_robots)

def print_robots_per_type(df):
    robot_types = df['robot_type'].unique()
    distinct_robot_types = df.groupby(df['id'].str[:4])['id'].nunique()
    print(robot_types)
    for robot_type in robot_types:
        id_subset = df.where(df['robot_type'] == robot_type)
        distinct_robots = id_subset.groupby(id_subset['id'].str[:4])['robot'].nunique()
        print(distinct_robots)


def interpolate_sequence(df, id, interval=0.01, cols = ['timeindex', 'torqueactual'], part_of_a_group=False):
    col1 = cols[0]
    col2 = cols[1]
    subset = df[df['id'] == id][['id', col1, col2]]
    
    # Create a complete time range with the desired interval
    max_time = subset[col1].max()
    full_time_range = np.arange(0.01, max_time, interval)
    
    # Merge the full time range with the original timestamps
    full_time_df = pd.DataFrame({'id': id, col1: full_time_range, col2: np.nan})
    full_time_df = full_time_df[~full_time_df[col1].isin(subset[col1])]
    merged_df = pd.concat([subset, full_time_df], axis=0)

    # Sort the values by timeindex
    merged_df = merged_df.sort_values(by=col1)

    # Set the timeindex as the index
    merged_df = merged_df.set_index(col1, drop=False)
    
    # Interpolate missing values
    merged_df[col2] = merged_df[col2].interpolate(method='slinear')
    
    # Keep only the consistent timestamps

    result = merged_df[merged_df[col1].isin(full_time_range)]

    if not part_of_a_group:
        nan_values = np.isnan(result[col2]).sum()
        if nan_values == 1:
            result.loc[result[col1] == interval, col2] = result.loc[result[col1] == 2*interval, col2].values
        elif nan_values > 1:
            print('CAREFUL: There are NaN values in the interpolated sequence: ' + id)
    
    return result

def interpolate_sequences(df, ids, interval=0.01):
    ids = df['id'].unique()
    interpolated_df = pd.DataFrame()
    for id in ids:
        interpolated_sequence = interpolate_sequence(df, id, interval, True)
        interpolated_df = pd.concat([interpolated_df, interpolated_sequence], axis=0)

    #In the following two lines of code I am replacing the first value of the torqueactual column with the second value of the torqueactual column for the ids that have NaN values in the torqueactual column.
    #This is because the interpolation method sometimes does not work for the first value of the torqueactual column.

    ids_w_nan = interpolated_df[np.isnan(interpolated_df['torqueactual'])]['id'].unique()
    interpolated_df.loc[(interpolated_df['id'].isin(ids_w_nan)) & (interpolated_df['timeindex'] == interval), 'torqueactual'] = interpolated_df.loc[(interpolated_df['id'].isin(ids_w_nan)) & (interpolated_df['timeindex'] == 2*interval), 'torqueactual'].values
    interpolated_df = interpolated_df.reset_index(drop=True)

    nan_values = np.isnan(interpolated_df['torqueactual']).sum()

    if nan_values > 0:
        print('CAREFUL: There are NaN values in the interpolated sequences')

    return interpolated_df