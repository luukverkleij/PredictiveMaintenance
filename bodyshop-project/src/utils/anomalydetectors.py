import pandas as pd
import numpy as np

from abc import ABC, abstractmethod
from functools import reduce
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest

import src.utils.globals as g

class AnomalyDetector(ABC):
    def __init__(self, column_name):
        self.model = None
        self.column_name = column_name

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
    
class ZScore(AnomalyDetector):
    def __init__(self, n_neighbors=20, aggr=None):
        super().__init__(column_name="z")
        self.columns = None
        self.aggr = None

    def fit(self, df, columns, verbose):
        self.model = df[['timeindex_bin']].copy()
        self.columns = columns

        for col in columns:
            self.model[f'{col}_mean'] = df[col].mean()
            self.model[f'{col}_std'] = df[col].std()

            self.model[f'{col}_zscore'] = np.abs((df[col] - self.model[f'{col}_mean']) / self.model[f'{col}_std'])

        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")
        
        if self.aggr == None:
            self.aggr = lambda x : np.sum(x, axis=1) / len(columns)
        
        zscore = self.aggr(self.model[[f'{col}_zscore' for col in columns]])
        
        return zscore
    
class MZScore(AnomalyDetector):
    def __init__(self, n_neighbors=20, aggr=None):
        super().__init__(column_name="mz")
        self.columns = None
        self.aggr = None

    def fit(self, df, columns, verbose):
        self.model = df[['timeindex_bin']].copy()
        self.columns = columns

        for col in columns:
            self.model[f'{col}_mean'] = df[col].mean()
            self.model[f'{col}_mad'] = df[col].std()

            self.model[f'{col}_mzscore'] = np.abs((0.6745*(df[col] - self.model[f'{col}_mean'])) / self.model[f'{col}_mad'])

        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")
        
        if self.aggr == None:
            self.aggr = lambda x : np.sum(x, axis=1) / len(columns)
        
        mzscore = self.aggr(self.model[[f'{col}_mzscore' for col in columns]])
        
        return mzscore

class LOF(AnomalyDetector):
    def __init__(self, n_neighbors=20):
        super().__init__(column_name='lof')
        self.model = LocalOutlierFactor(n_neighbors=n_neighbors)

    def fit(self, df, columns, verbose):
        self.model.fit(df[['timeindex_bin'] + columns])
        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")  
        
        return pd.Series(-self.model.negative_outlier_factor_, index=df.index)
    
class IF(AnomalyDetector):
    def __init__(self, n_neighbors=20):
        super().__init__(column_name='if')
        self.model = IsolationForest(n_estimators = 500, contamination = 0.02, random_state = 42, n_jobs = -1)

    def fit(self, df, columns, verbose):
        X = df[['timeindex_bin'] + columns]
        self.model.fit(X.values)
        self.scores = self.model.score_samples(X.values)
        return self

    def score(self, df, columns):
        if self.model is None:
            raise ValueError("Model has not been fitted yet.")  
        
        return pd.Series(self.scores, index=df.index)