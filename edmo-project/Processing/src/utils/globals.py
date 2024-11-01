import numpy as np

# Settings
globals_test_data = True
data_folder_path = "data" if not globals_test_data else "data-test"
experiments_folder_path = "experiments/" if not globals_test_data else "experiments-test/"

# Databases paths
path_imu_raw            = data_folder_path + '/imu-raw.parquet'
path_motor_raw          = data_folder_path + '/motor-raw.parquet'

path_motor              = data_folder_path + "/motor.parquet"
path_imu                = data_folder_path + "/imu.parquet"
path_series             = data_folder_path + '/series.parquet'

path_motor_results      = data_folder_path + "/motor_results.parquet"
path_imu_results        = data_folder_path + "/imu_results.parquet"
path_series_results     = data_folder_path + "/series_results.parquet"

path_imu_syn            = data_folder_path + "/imu_syn.parquet"
path_imu_syn_results    = data_folder_path + "/imu_syn_results.parquet"

# IMU Sensor Constants
imu_sensor3 = ['acceleration', 'gravity', 'gyroscope', 'magnetic']
imu_sensor4 = ['rotation']
imu_sensors = imu_sensor3 + imu_sensor4
imu_sensors_real = ['acceleration', 'gyroscope', 'magnetic']

imu_axes3 = ['x', 'y', 'z']
imu_axes4 = imu_axes3 + ['real']

imu_sensor_axes     = [(sensor, imu_axes3) for sensor in  imu_sensor3] + [(sensor, imu_axes4) for sensor in imu_sensor4]
imu_sensors_u  = [f'{sensor}_{axis}' for (sensor, axes) in  imu_sensor_axes for axis in axes]

imu_sensor_real_axes     = [(sensor, imu_axes3) for sensor in  imu_sensors_real] 
imu_sensors_real_u  = [f'{sensor}_{axis}' for sensor in  imu_sensors_real for axis in imu_axes3]
imu_sensors_real_u2 = [[f'{sensor}_{axis}' for axis in imu_axes3] for sensor in imu_sensors_real]

# Motor Sensor Constants
motor_sensors = ['output']
motor_axes = ['0', '1', '2']

motor_sensor_axes = [(sensor, motor_axes) for sensor in  motor_sensors]
motor_sensors_u = [f'{sensor}_{axis}' for sensor in motor_sensors for axis in motor_axes]

# Misc Constants
methods = ['z', 'mz', 'lof', 'if']


# def cal_outliers_threshold_prec(df, columns, thresholdprec):
#     #First calculate the thresholds such there are (as close to) thresholdprec outliers.

#     func = lambda x : np.sum(abs(x) >= threshold)
#     agg_dict = {col : func for col in columns}
    
#     return df.groupby(['seqid']).agg(agg_dict).reset_index()
