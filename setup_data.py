import pandas as pd
import numpy as np

SOURCE_FILE = "data.csv"

def setup_datasets():

    print("--- SETTING UP LOCAL DATASETS ---")

    df = pd.read_csv(SOURCE_FILE)

    # shuffle dataset
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # split dataset
    splits = np.array_split(df, 3)

    for i, subset in enumerate(splits):

        subset = pd.DataFrame(subset)

        filename = f"dataset_owner_{i+1}.csv"

        subset.to_csv(filename, index=False)

        print(f"Created {filename} with {len(subset)} rows")

if __name__ == "__main__":
    setup_datasets()