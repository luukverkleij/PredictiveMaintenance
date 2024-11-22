import pandas as pd
import numpy as np

from abc import ABC, abstractmethod
from functools import reduce
from scipy.stats import median_abs_deviation
from scipy.spatial.distance import mahalanobis
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from sklearn.covariance import MinCovDet


import src.utils.globals as g

#
# AnomalyDetector
#
class AnomalyDetector(ABC):
    def __init__(self, column_name):
        self.model = None
        self.name = self.column_name = column_name

    @abstractmethod
    def fit(self, df, columns, verbose=False):
        pass

    @abstractmethod
    def score(self, df, columns):
        pass

    def fit_score(self, df, columns, verbose=False):
        if verbose:
            print(f"Start fitting {self.column_name}")
            
        self.fit(df, columns, verbose)

        if verbose:
            print(f"Fitting {self.column_name} done")

        df[self.column_name] = self.score(df, columns)

        return df[['seqid', 'timeindex_bin', self.column_name]]

#
# ZScore
#
class ZScore(AnomalyDetector):
    def __init__(self, n_neighbors=20, aggr=None):
        super().__init__(column_name="z")
        self.columns = None
        self.aggr = None

    def fit(self, df, columns, verbose):
        df = df.reset_index(drop=True)
        self.model = df[columns[0]].copy()
        self.columns = columns
        col_time = 'timeindex_bin'

        for col in columns[1]:
            mean_std_cols = df.groupby(col_time)[col].agg(**{f'{col}_mean' : 'mean', f'{col}_std' : 'std'}).reset_index()

            self.model = pd.merge(self.model, mean_std_cols, on=col_time, how='left')
            self.model[f'{col}_zscore'] = np.abs((df[col] - self.model[f'{col}_mean']) / self.model[f'{col}_std'])

        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")
        
        if self.aggr == None:
            self.aggr = lambda x : np.sum(x, axis=1) / len(columns[1])
        
        zscore = self.aggr(self.model[[f'{col}_zscore' for col in columns[1]]])
        
        return zscore
    
#
# MZScore
# 
class MZScore(AnomalyDetector):
    def __init__(self, n_neighbors=20, aggr=None):
        super().__init__(column_name="mz")
        self.columns = None
        self.aggr = None

    def fit(self, df, columns, verbose):
        df = df.reset_index(drop=True)
        self.model = df[columns[0]].copy()
        self.columns = columns
        col_time = 'timeindex_bin'

        for col in columns[1]:
            mean_std_cols = df.groupby(col_time)[col].agg(**{f'{col}_mean' : 'mean', f'{col}_mad' : median_abs_deviation}).reset_index()

            self.model = pd.merge(self.model, mean_std_cols, on=col_time, how='left')
            self.model[f'{col}_mzscore'] = np.abs((0.6745*(df[col] - self.model[f'{col}_mean'])) / self.model[f'{col}_mad'])
            self.model[f'{col}_mzscore'] = np.where(np.isinf(self.model[f'{col}_mzscore']) | (np.abs(self.model[f'{col}_mzscore']) > np.finfo(np.float64).max), 
                                                    1, 
                                                    self.model[f'{col}_mzscore'])
        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")
        
        if self.aggr == None:
            self.aggr = lambda x : np.sum(x, axis=1) / len(columns[1])
        
        zscore = self.aggr(self.model[[f'{col}_mzscore' for col in columns[1]]])
        
        return zscore
    
#
# LOF
#
class LOF(AnomalyDetector):
    def __init__(self, n_neighbors=20, name="lof"):
        super().__init__(column_name=f"{name}_{n_neighbors}")
        self.model = LocalOutlierFactor(n_neighbors=n_neighbors)
        self.scores = None

    def fit(self, df, columns, verbose):
        X = df[["timeindex"] + columns[1]]

        self.model.fit(X.values)
        self.scores = pd.Series(-self.model.negative_outlier_factor_, index=X.index)
        return self

    def score(self, df, columns):
        if self.scores is None:
            raise ValueError("Model has not been fitted yet.")
        
        return self.scores

#
# IF
#   
class IF(AnomalyDetector):
    def __init__(self, n_neighbors=20):
        super().__init__(column_name='if')
        self.model = IsolationForest(n_estimators = 500, contamination = 0.02, random_state = 42, n_jobs = -1)

    def fit(self, df, columns, verbose):
        X = df[['timeindex'] + columns[1]]
        self.model.fit(X.values)
        self.scores = 1 - self.model.score_samples(X.values)
        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")  
        
        return pd.Series(self.scores, index=df.index)
    
