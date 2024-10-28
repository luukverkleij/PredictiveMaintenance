import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.stats import median_abs_deviation
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import MinMaxScaler

import utils.globals as g

n_estimators    = 500
contamination   = 0.02
random_state    = 42

def calc_methods(df, sensorsaxes=g.imu_sensor_real_axes, verbose=False):
    if verbose:
        print("calculating (m)z-scores")
    df_result = calc_scores(df, sensorsaxes)

    if verbose:
        print("calculating lof")
    df_result = calc_lof(df_result, sensorsaxes, verbose)

    if verbose:
        print("calculating if")
    df_result = calc_if(df_result, sensorsaxes, verbose)

    return df_result

def calc_lof(df, sensorsaxes, verbose=False):
    def _cal_lof(df, columns, colname):
        lof = LocalOutlierFactor()
        lof.fit(df[['timeindex_bin'] + columns])
        df[colname] = -lof.negative_outlier_factor_
        return df

    # IMU
    for sensor,axes in sensorsaxes:
        if verbose:
            print(f"Fitting lof_{sensor}")
        _cal_lof(df, [f'{sensor}_{axis}' for axis in axes], f'lof_{sensor}')

    return df


def calc_if(df, sensorsaxes, verbose=False):
    iso_forest= IsolationForest(n_estimators=n_estimators, contamination=contamination, n_jobs=-1)

    for sensor, axes in sensorsaxes:
        X = df[['timeindex_bin'] + [f'{sensor}_{axis}' for axis in axes]]

        if verbose:
            print(f"Fitting if_{sensor}")
        df[f'if_{sensor}'] = iso_forest.fit(X).score_samples(X) * -1

    return df

#
# Scores
#

def calc_scores(df, sensorsaxes):
    df = _calc_mz_z_scores(df, [f'{sensor}_{axis}' for (sensor, axes) in sensorsaxes for axis in axes])

    for (sensor, axes) in sensorsaxes:
        df = _combine_mz_z_scores(df, sensor, axes)

    return df


def _calc_mz_z_scores(df, columns):
    agg_funcs = ['mean', 'std', median_abs_deviation]

    df_tmp = df.groupby('timeindex_bin', as_index=False).agg({col : agg_funcs for col in columns})
    df_tmp.columns = [col[0] if col[0] == 'timeindex_bin' else '_'.join(col).strip()  for col in df_tmp.columns]

    df = df.merge(df_tmp, on=['timeindex_bin'])
    for x in columns:
        df[f'z_{x}'] = (df[x] - df[x + '_mean']) / df[x + '_std']
        df[f'mz_{x}'] = (0.6745*(df[x] - df[x + '_mean'])) / df[x + '_median_abs_deviation']

    return df.drop(columns=[col for col in df_tmp.columns if any(col.endswith(suffix) for suffix in ['mean', 'std', 'median_abs_deviation'])])

def _combine_mz_z_scores(df, sensor, axes, squared=False):
    func = np.abs if not squared else np.sqrt
    
    z_cols = [f'z_{sensor}_{axis}' for axis in axes]
    mz_cols = [f'mz_{sensor}_{axis}' for axis in axes]

    df[f'z_{sensor}'] = func(df[z_cols]).sum(axis=1) / len(z_cols)
    df[f'mz_{sensor}'] = func(df[mz_cols]).sum(axis=1) / len(mz_cols)

    return df.drop(columns=z_cols + mz_cols)
