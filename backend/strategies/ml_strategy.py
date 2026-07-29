# retrains every api call, nothing saved to disk

from backtester.walk_forward import run_single_split, run_walk_forward


def run(df, walk_forward: bool = False, n_folds: int = 3):
    """returns (df with signal, validation meta). walk_forward=True → expanding folds."""
    # thin wrapper - keeps app.py from importing walk_forward directly
    if walk_forward:
        return run_walk_forward(df, n_folds=n_folds)
    # default: one chronological 70/30 hold-out
    return run_single_split(df, train_frac=0.7)
