import pandas as pd
import numpy as np

from functools import reduce
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest

import utils.globals as g

n_estimators    = 500
contamination   = 0.02
random_state    = 42
n_jobs          = -1

def calc_methods(df, methods=['lof'], verbose=True, all=False, save=None):
    results = []

    if 'scores' in methods:
        results += [calc_scores(df, verbose)]
        if save:
            _save(results, save)
    if 'lof' in methods:
        results += [calc_lof(df, verbose, all)]
        if save:
            _save(results, save)
    if 'if' in methods:
        results += [calc_if(df, verbose, all)]
        if save:
            _save(results, save)

    if save:
        _save(results, save)
    return reduce(lambda x, y: pd.merge(x, y, on = g.tracks_result_columns), results)

def _save(dfs, path):
    df = reduce(lambda x, y: pd.merge(x, y, on = g.tracks_result_columns), dfs)
    df.to_parquet(path)

#
# Z & MZ-Score
#

def _calc_scores_intermediate(df):
    #print(df)
    df['torqueactual_mean'] = df['torqueactual'].mean()
    df['torqueactual_std'] = df['torqueactual'].std()
    df['torqueactual_mad'] = median_abs_deviation(df['torqueactual'])
    return df

def _calc_scores(df):
    df = _calc_scores_intermediate(df)
    df['z'] = np.abs((df['torqueactual'] - df['torqueactual_mean']) / df['torqueactual_std'])
    df['mz'] = np.abs((0.6745*(df['torqueactual'] - df['torqueactual_mean'])) / df['torqueactual_mad'])
    return df

def calc_scores(df, verbose=False):
    if verbose:
        print('calculating scores')
    
    result = df.groupby('robotid').apply(_calc_scores).reset_index(drop=True)
    return result[g.tracks_result_columns + ['z', 'mz']]

#
# For every robotid, fitting an Local Outlier Factor Model
#
def calc_lof(df, verbose=True, all=False):
    lof = LocalOutlierFactor()

    def calculate_lof(df, colname='lof'):  
        if verbose:
            print(f'lof fitting {df["robotid"].unique()}')
        lof.fit(df[["timeindex_bin","torqueactual"]])  
        df[colname] = -lof.negative_outlier_factor_
        return df

    result = df.groupby('robotid').apply(calculate_lof).reset_index(drop=True)

    if all:
        result = calculate_lof(result, 'lof_all')

    return result[g.tracks_result_columns + ['lof']]

#
# Isolation Forest
#
def calc_if(df, verbose=True, all=False):
    iso_forest      = IsolationForest(n_estimators=n_estimators, contamination=contamination, n_jobs=n_jobs)

    def calculate_if(df, colname='if'):
        if verbose:
            print(f'if fitting {df["robotid"].unique()}')

        X = df[['timeindex_bin', 'torqueactual']]
        df[colname] = iso_forest.fit(X).score_samples(X) * -1
        return df

    result = df.groupby('robotid').apply(calculate_if).reset_index(drop=True)

    if all:
        result = calculate_if(result, 'if_all')

    return result[g.tracks_result_columns + ['if']]



#
# Stuff
#

def sample_sequences(df, num):
    ids = sample_sequence_ids(df, num)
    return df[df['seqid'].isin(ids)]

def sample_sequence_ids(df, num):
    ids = df['seqid'].unique()
    return np.random.choice(ids, num, replace=False)
