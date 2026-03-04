import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import random

from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample

# ---- GLOBAL SEED (stabilizes results) ----
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)


class HybridDL(nn.Module):

    def __init__(self, input_dim):
        super(HybridDL, self).__init__()

        self.model = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),

            nn.Linear(128, 64),
            nn.ReLU(),

            nn.Linear(64, 32),
            nn.ReLU(),

            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.model(x)


def preprocess_data(df):

    df = df.copy()

    # split features and label
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    # remove bad values
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    # scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ----- BALANCE DATASET -----
    df_balanced = pd.DataFrame(X_scaled)
    df_balanced["label"] = y.values

    majority = df_balanced[df_balanced.label == 0]
    minority = df_balanced[df_balanced.label == 1]

    if len(minority) > 0:

        minority_up = resample(
            minority,
            replace=True,
            n_samples=len(majority),
            random_state=SEED
        )

        df_balanced = pd.concat([majority, minority_up])

    X_final = df_balanced.iloc[:, :-1].values
    y_final = df_balanced.iloc[:, -1].values

    return X_final, y_final


def apply_ldp(X, epsilon=20.0):

    # stable noise generation
    np.random.seed(SEED)

    noise = np.random.laplace(0, 1/epsilon, X.shape)

    return X + noise


def generate_dummy_data(rows=200):

    np.random.seed(SEED)

    X = np.random.rand(rows, 20)
    y = np.random.randint(0, 2, rows)

    df = pd.DataFrame(X)
    df["label"] = y

    return df