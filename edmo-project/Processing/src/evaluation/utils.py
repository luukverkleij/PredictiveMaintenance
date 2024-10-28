import numpy as np
import utils.globals as g
import matplotlib.pyplot as plt

from functools import partial
from sklearn.metrics import precision_recall_curve

def aggregate_scores(df, columns, funcs):    
    agg_dict = {col: funcs[i] for i, col in enumerate(columns)} | {'timeindex_bin' : 'count'}
    agg_df = df.groupby(['seqid']).agg(agg_dict).reset_index()
    
    for col in columns:
            agg_df[col] = agg_df[col] / agg_df['timeindex_bin']
            
    return agg_df

def aggr_sum(df, columns):
    return aggregate_scores(df, columns, [lambda x : np.sum(abs(x))]*len(columns))

def aggr_count_threshold_crossings(df, columns, thresholds):
    _threshold_func = lambda t, x : np.sum(abs(x) >= t)
    funcs2 = [partial(_threshold_func, t) for t in thresholds]
    return aggregate_scores(df, columns, funcs2)

def aggr_squaredsum(df, columns):
    return aggregate_scores(df, columns, [lambda x : np.sum(x**2)]*len(columns))


def count_by_thresholds(df, columns, thresholds):
    _threshold_func = lambda t, x : np.sum(abs(x) >= t)
    funcs2 = [partial(_threshold_func, t) for t in thresholds]

    agg_dict = {col : funcs2[i] for i, col in enumerate(columns)}
    
    return df.groupby(['seqid']).agg(agg_dict).reset_index()

def count_by_thresholds_method(df, methodname, thresholds):
    return count_by_thresholds(_get_method_columns(methodname), thresholds)


#
# Plotting Functions
#

def _calc_f1(precision, recall):
    return 2 * (precision*recall)/(precision + recall)

def _calc_rpccurves(df, columns):
    return {col : precision_recall_curve(df['anomalous'], df[col]) for col in columns}

def plot_rpcurves(df, columns, showthresholds=True, title="", colnums=2, f1=True):
    # Calculte the rpc curves
    rpcurves = _calc_rpccurves(df, columns)

    # Calculate the number of rows needed
    cols = colnums
    num_plots = len(rpcurves)
    rows = (num_plots + cols - 1) // cols  # Ceiling division to ensure enough rows

    # Create a figure with subplots
    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 5*rows))

    # Flatten axes for easy indexing if needed
    axes = axes.flatten()

    # Loop through the DataFrames and plot each in the corresponding subplot
    for i, (name, prcurve) in enumerate(rpcurves.items()):
        _plot_rpcurve(prcurve, name, axes[i], showthresholds, f1)

    # Hide any unused subplots
    for j in range(i+1, len(axes)):
        fig.delaxes(axes[j])

    plt.suptitle(title)
    plt.tight_layout()

    # Show the plot
    plt.show()

def _plot_rpcurve(prcurve, name, axis, showthresholds=True, f1=True):
    if showthresholds:
        axis.plot(prcurve[2], prcurve[0][:-1], label="precision")
        axis.plot(prcurve[2], prcurve[1][:-1], label="recall")
        if f1:
            axis.plot(prcurve[2], _calc_f1(prcurve[0][:-1], prcurve[1][:-1]), label="F1")
    else:
        axis.plot(prcurve[0][:-1], prcurve[1][:-1], label="precision-recall")
        axis.set_xlim(0, 1)

    axis.legend()
    axis.set_title(name)
    axis.set_ylim(0, 1) 

def _get_sensor_columns(sensor, methods=['z','mz','lof','if']):
    return [f'{method}_{sensor}' for method in methods]

# 
# Plotting Functions by method (OLD)
#

def plot_rpcurves_method(df, methodname, showthresholds=True, title="", colnums=3):
    # Calculte the rpc curves
    rpcurves = _calc_rpccurves_method(df, methodname)

    # Calculate the number of rows needed
    cols = colnums
    num_plots = len(rpcurves)
    rows = (num_plots + cols - 1) // cols  # Ceiling division to ensure enough rows

    # Create a figure with subplots
    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 5*rows))

    # Flatten axes for easy indexing if needed
    axes = axes.flatten()

    # Loop through the DataFrames and plot each in the corresponding subplot
    for i, (name, prcurve) in enumerate(rpcurves.items()):
        _plot_rpcurve_method(prcurve, name, axes[i], showthresholds)

    # Hide any unused subplots
    for j in range(i+1, len(axes)):
        fig.delaxes(axes[j])

    plt.suptitle(title)
    plt.tight_layout()

    # Show the plot
    plt.show()


def _plot_rpcurve_method(prcurve, name, axis, showthresholds=True, f1=True):
    if showthresholds:
        axis.plot(prcurve[2], prcurve[0][:-1], label="precision")
        axis.plot(prcurve[2], prcurve[1][:-1], label="recall")
        if f1:
            axis.plot(prcurve[2], 2 * (prcurve[0][:-1]*prcurve[1][:-1])/(prcurve[0][:-1] + prcurve[1][:-1]), label="F1")
    else:
        axis.plot(prcurve[0][:-1], prcurve[1][:-1], label="precision-recall")
        axis.set_xlim(0, 1)

    axis.legend()
    axis.set_title(name)
    axis.set_ylim(0, 1) 

def _calc_rpccurves_method(df, methodname):
    columns = _get_method_columns(methodname)
    return _calc_rpcurves_method_c(df, columns)

def _calc_rpcurves_method_c(df, columns):
    rpc_dict = {col : precision_recall_curve(df['anomaly'] != "none", df[col]) for col in columns}
    return rpc_dict


def _plot_rpcurve_solo():
    pass

#
# Underscore util functions
#

def _get_sensor_columns(sensor, methods=['z','mz','lof','if']):
    return [f'{method}_{sensor}' for method in methods]

def _get_method_columns(methodname):
    return[f'{methodname}_{x}' for x in g.imu_sensors]
