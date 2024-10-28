import numpy as np
import utils.globals as g
import matplotlib.pyplot as plt

from functools import partial
from sklearn.metrics import precision_recall_curve


#
# Plotting Functions
#

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
            axis.plot(prcurve[2], 2 * (prcurve[0][:-1]*prcurve[1][:-1])/(prcurve[0][:-1] + prcurve[1][:-1]), label="F1")
    else:
        axis.plot(prcurve[0][:-1], prcurve[1][:-1], label="precision-recall")
        axis.set_xlim(0, 1)

    axis.legend()
    axis.set_title(name)
    axis.set_ylim(0, 1) 