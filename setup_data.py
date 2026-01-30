import pandas as pd
import numpy as np
import os

# --- CONFIGURATION ---
SOURCE_FILE = "final_augmented_data.csv"  # Ensure your file is named this
TARGET_COL = "Diabetes_binary" # The name of your target column

def setup_datasets():
    print("--- SETTING UP LOCAL DATASETS ---")
    
    # 1. Load Master Dataset
    if os.path.exists(SOURCE_FILE):
        print(f"Loading real data from {SOURCE_FILE}...")
        df = pd.read_csv(SOURCE_FILE)
    else:
        print(f"❌ Error: {SOURCE_FILE} not found. Please ensure the CSV is in this folder.")
        return

    # 2. CRITICAL FIX: Move Target Column to the End
    # The FL model in fl_utils.py assumes y = df.iloc[:, -1] (The last column)
    # Your data has the target at the start, so we must move it.
    if TARGET_COL in df.columns:
        print(f"Found target '{TARGET_COL}'. Moving it to the last column...")
        # Get all columns except target, then append target at the end
        cols = [c for c in df.columns if c != TARGET_COL] + [TARGET_COL]
        df = df[cols]
    else:
        print(f"⚠️ Warning: Target '{TARGET_COL}' not found. Using the existing last column as target.")

    # 3. Shuffle Data
    df = df.sample(frac=1).reset_index(drop=True)

    # 4. Split into 3 Parts (Simulating 3 Hospitals)
    splits = np.array_split(df, 3)

    # 5. Save to Owner-Specific Files
    for i, subset in enumerate(splits):
        owner_id = i + 1
        filename = f"dataset_owner_{owner_id}.csv"
        subset.to_csv(filename, index=False)
        print(f"✅ Created {filename} ({len(subset)} rows) -> For Owner {owner_id}")

if __name__ == "__main__":
    setup_datasets()