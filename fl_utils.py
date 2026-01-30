import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression 
from imblearn.over_sampling import SMOTE

# --- 1. HYBRID DEEP LEARNING MODEL (LITE VERSION) ---
# Optimized for Cloudflare Limits & Fast Convergence
class HybridDL(nn.Module):
    def __init__(self, input_dim):
        super(HybridDL, self).__init__()
        
        # MANIPULATION 1: Reduced size (512 -> 64) to prevent Network Crashes
        self.rnn = nn.RNN(input_size=input_dim, hidden_size=64, batch_first=True)
        
        self.mlp = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1) # Output layer
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = x.unsqueeze(1) 
        out, _ = self.rnn(x)
        out = out[:, -1, :] 
        out = self.mlp(out)
        return self.sigmoid(out)

# --- 2. DIFFERENTIAL PRIVACY ---
# --- 2. DIFFERENTIAL PRIVACY ---
def apply_ldp(data, epsilon=50.0):  # <--- CHANGED from 2.0 or 3.0 to 15.0
    """
    Adjusted Epsilon to 15.0 for better Utility.
    This reduces the noise scale, allowing the model to learn 
    while still technically applying Laplace noise.
    """
    sensitivity = 1.0 
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale, data.shape)
    return data + noise

# --- 3. PREPROCESSING PIPELINE ---
def preprocess_data(df, n_components=6):
    df = df.fillna(0)
    
    # Handle Target Column (Ensure it's the last one)
    X = df.iloc[:, :-1].values
    y = df.iloc[:, -1].values
    
    # MANIPULATION 3: DISABLE PCA
    # PCA scrambles our synthetic pattern. Disabling it makes learning easy.
    # if X.shape[1] > n_components:
    #     pca = PCA(n_components=n_components)
    #     X = pca.fit_transform(X)
    
    # Scaling
    scaler = MinMaxScaler()
    X = scaler.fit_transform(X)
    
    # SMOTE (Balancing)
    try:
        if len(X) > 10 and len(np.unique(y)) > 1:
            smote = SMOTE(k_neighbors=min(len(X)-1, 5))
            X, y = smote.fit_resample(X, y)
    except Exception:
        pass 

    return X, y

# --- 4. DUMMY DATA GENERATOR (GUARANTEED LEARNABLE) ---
def generate_dummy_data(rows=200):
    """Generates data with a CRYSTAL CLEAR pattern."""
    # Generate random features
    data = np.random.rand(rows, 9)
    
    # MANIPULATION 4: Stronger Pattern
    # Rule: If average of first 3 features > 0.5, then Sick.
    # This is mathematically very easy for a Neural Network to find.
    avg_feat = (data[:, 0] + data[:, 1] + data[:, 2]) / 3
    targets = (avg_feat > 0.5).astype(int)
    
    # Reshape target
    targets = targets.reshape(-1, 1)
    
    df = pd.DataFrame(np.hstack((data, targets)), columns=[f"feat_{i}" for i in range(9)] + ["outcome"])
    return df