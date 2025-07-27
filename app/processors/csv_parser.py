import pandas as pd

def read_metrics_csv(path: str) -> str:
    """Read and return first 10 rows of CSV as a string."""
    df = pd.read_csv(path)
    return df.head(10).to_csv(index=False)
