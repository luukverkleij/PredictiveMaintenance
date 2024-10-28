import pickle
import pandas as pd
import concurrent.futures

from typing import Self
from datetime import datetime
from functools import reduce
from sklearn.metrics import precision_recall_curve, auc, roc_curve
from concurrent.futures import wait, FIRST_COMPLETED

import src.utils.anomalydetectors as m
import src.utils.globals as g

from src.utils.plotting import plot_rpcurves

class Experiment:
    def __init__(self, name : str = ""):
        self.name = name
        if self.name == "":
            self.name = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        self.results = {
            'df' : pd.DataFrame(),
            'pr' : {},
            'roc' : {},
            'auc-pr' : {},
            'auc-roc' : {},
        }
        self.progress = pd.DataFrame()
        self.anomalies = pd.DataFrame()

    def run(self, df, models : dict[str, m.AnomalyDetector], columns : list[str], spliton=None, verbose=False):
        self.results['df'] = df[['seqid', 'timeindex_bin']].copy()
        #models_results = {model : [] for model in self.models.keys()}
        dfs = [df]

        if spliton:
            dfs = [group for _, group in df.groupby(spliton)]

        if verbose:
            self.progress = pd.DataFrame({model: [f"0/{len(dfs)}"] for model in models.keys()})
            #print(self.progress.to_string(index=False))

        # Let's for every method apply a futures thing...
        def model_fit_scores(name, model, dfs, columns, verbose):
            print(f"model_fit_scores {name} for {len(dfs)} on {columns}")
            r = []
            for df in dfs:
                r += [model.fit_score(df, columns, verbose)]
                self.verbose_progress(name, len(dfs))

            return r
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(model_fit_scores, name, model, dfs, columns, False) : name 
                for name, model in models.items()
            }

            while futures:
                # Wait until the first future completes
                done, _ = wait(futures, return_when=FIRST_COMPLETED)

                for future in done:

                    # Retrieve the model name and result
                    name = futures[future]
                    results = pd.concat(future.result())

                    self.results['df'] = self.results['df'].merge(results, on=['seqid', 'timeindex_bin'])

                    # Remove the processed future from the futures dict
                    del futures[future]

        return self

    def calculate_metrics(self, models, aggrfunc, df_anomalous=pd.DataFrame()):     
        if df_anomalous.empty:
            df_anomalous = self.anomalies

        # Calculate series df here
        dfs_series = []
        for (name,_) in models.items():
            dfs_series += [aggrfunc(self.results['df'], [name])]

        df_series = reduce(lambda x, y: pd.merge(x, y, on = 'seqid'), dfs_series)
        df = pd.merge(df_series, df_anomalous, on='seqid')
        

        for (name,_) in models.items():
                self.results['pr'][name]    = precision_recall_curve(df['anomalous'], df[name])
                self.results['auc-pr'][name]  = auc(self.results['pr'][name][1], self.results['pr'][name][0])

                self.results['roc'][name]   = roc_curve(df['anomalous'], df[name])
                self.results['auc-roc'][name]  = auc(self.results['roc'][name][0], self.results['roc'][name][1])

        return self
    
    def set_anomalies(self, df_anomalies):
        self.anomalies = df_anomalies
    
    def verbose_progress(self, method, total):
        # Update
        self.progress.at[0, method] = f"{int(self.progress.at[0, method].split('/')[0]) + 1}/{total}"

        # Clear & Print
        #clear_output(wait=True)
        print(self.progress.to_string(index=False), end='\r')
    
    def plot_rp(self, thresholds=True):
        plot_rpcurves(self.results['pr'])

    def pickle(self):
        with open(self.path(self.name), 'wb') as f:
            pickle.dump(self, f)

    def get(self, key):
        return self.results['key']
    
    @classmethod
    def unpickle(cls, name) -> Self:
        with open(cls.path(name), 'rb') as f:
            return pickle.load(f)
        
    @classmethod
    def path(cls, name):
        return g.experiments_folder_path + f'{name}'
    