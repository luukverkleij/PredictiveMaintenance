import pandas as pd
from hmmlearn.hmm import GMMHMM
import numpy as np
import re
import pickle


class HMM:
    def __init__(self, **kwargs):
        self.hyperparameters = kwargs
        self.columns = kwargs.get("columns", ["torqueactual"])

        self.n_components = kwargs.get("n_components", 50)
        self.covariance_type = kwargs.get("covariance_type", "full")
        self.implementation = kwargs.get("implementation", "log")

        self.model = GMMHMM(
            n_components=self.n_components,
            covariance_type=self.covariance_type,
            implementation=self.implementation,
            verbose=True,
        )

    def fit(self, X: pd.DataFrame):
        X, lengths = self._prepare_data(X)
        self.model.fit(X, lengths=lengths)
        print(f"Model trained - Log-probability: {self.model.monitor_.history[-1]:.2f}")

    def fit_seach(
        self, X: pd.DataFrame, min_n_components=10, max_n_components=100, step=10
    ):
        min_logprob = -np.inf
        best_model = None
        for i in range(min_n_components, max_n_components, step):
            self.model.n_components = i
            self.fit(X)

            if self.model.monitor_.history[-1] > min_logprob:
                min_logprob = self.model.monitor_.history[-1]
                best_model = self.model

        self.model = best_model
        print(
            f"Best model with {self.model.n_components} components"
            f"- Log-probability: {self.model.monitor_.history[-1]:.2f}"
        )

    def posterior_prob(self, X, prep_data=True):
        if prep_data:
            X, _ = self._prepare_data(X)
        return self.model.score(X)
    
    def score_samples(self, X, prep_data=True):
        if prep_data:
            X, _ = self._prepare_data(X)
        return self.model.score_samples(X)

    def _prepare_data(self, X):
        lengths = X.groupby("id").size().values
        X = X.sort_values("timeindex")
        X = X[self.columns].values.reshape(-1, len(self.columns))
        return X, lengths

    def save(self, alias=""):
        name = (
            f"{alias}_LL_{self.model.monitor_.history[-1]:.2f}"
            + "_".join([f"{k}_{v}" for k, v in self.hyperparameters.items()])
            + ".pkl"
        )
        path = f"models/hmm/{name}"
        with open(path, "wb") as file:
            pickle.dump(self.model, file)

    def load(self, name):
        self.columns = eval(re.search(r"\[.*?\]", name).group(0))
        with open(f"models/hmm/{name}", "rb") as file:
            self.model = pickle.load(file)
        return self
