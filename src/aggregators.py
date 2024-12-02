# Python file with methods that aggregate time series into a single anomaly value.

#region Imports
import numpy as np
#endregion 

#region Series Aggregation

#endregion

#region Aggregation Methods
# Aggregation Functions
def aggregate_scores(df, columns, funcs, normalize=True):    
    agg_dict = {col: funcs[i] for i, col in enumerate(columns)} | {'timeindex_bin' : 'count'}
    agg_df = df.groupby(['seqid']).agg(agg_dict).reset_index()

    if normalize:
        for col in columns:
            agg_df[col] = agg_df[col] / agg_df['timeindex_bin']
       
    agg_df = agg_df.drop(columns=['timeindex_bin'])    
    return agg_df

# Aggregation Methods
def aggr_sum(df, columns, normalize=True):
    return aggregate_scores(df, columns, [lambda x : np.sum(abs(x))]*len(columns), normalize)

def aggr_sqrtsum(df, columns, normalize=True):
    return aggregate_scores(df, columns, [lambda x : np.sum(x**2)]*len(columns), normalize)

# Aggregation Methods using Threshold
def aggr_count_threshold_crossings(df, columns, thresholds, normalize=True):
    funcs = [lambda x : np.sum(x >= t) for t in thresholds]
    return aggregate_scores(df, columns, funcs, normalize)

def aggr_sum_threshold_crossings(df, columns, thresholds, normalize=True):
    funcs = [lambda x : np.sum( [v if v >= t else 0 for v in x] ) for t in thresholds]
    return aggregate_scores(df, columns, funcs, normalize)

def aggr_sqrtsum_threshold_crossings(df, columns, thresholds, normalize=True):
    funcs = [lambda x : np.sum(([v**2 if v >= t else 0 for v in x])) for t in thresholds]
    return aggregate_scores(df, columns, funcs, normalize)
#endregion