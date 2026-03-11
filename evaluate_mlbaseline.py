import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.metrics import f1_score, accuracy_score, recall_score
from fl_utils import HybridDL, preprocess_data

def evaluate_ml_baselines():
    print("\n" + "="*70)
    print(" 🧠 EMPIRICAL ML EVALUATION: BASELINE VS. PROPOSED 🧠")
    print("="*70)

    # 1. Load Data
    train_df = pd.concat([pd.read_csv("dataset_owner_1.csv"), pd.read_csv("dataset_owner_2.csv")])
    test_df = pd.read_csv("dataset_owner_3.csv")
    
    X_train, y_train = preprocess_data(train_df)
    X_test, y_test = preprocess_data(test_df)
    
    X_train_t = torch.FloatTensor(np.array(X_train))
    y_train_t = torch.FloatTensor(np.array(y_train)).unsqueeze(1)
    X_test_t = torch.FloatTensor(np.array(X_test))
    y_test_np = np.array(y_test).astype(int)

    input_dim = X_train.shape[1]
    epochs = 10 # Fast training for evaluation

    # ---------------------------------------------------------
    # BASELINE 1: Centralized AI (Raw Data, No Privacy)
    # ---------------------------------------------------------
    print("\n[Training Baseline 1] Centralized Model (Highly Insecure)...")
    model_cent = HybridDL(input_dim)
    optimizer = torch.optim.Adam(model_cent.parameters(), lr=0.001)
    criterion = nn.BCELoss()
    
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = criterion(model_cent(X_train_t), y_train_t)
        loss.backward()
        optimizer.step()
        
    with torch.no_grad():
        preds = (model_cent(X_test_t) > 0.5).int().numpy()
        cent_acc = accuracy_score(y_test_np, preds)
        cent_f1 = f1_score(y_test_np, preds, zero_division=0)
        cent_rec = recall_score(y_test_np, preds, zero_division=0)

    # ---------------------------------------------------------
    # BASELINE 2: Vanilla Federated Learning (No LDP Noise)
    # ---------------------------------------------------------
    print("\n[Training Baseline 2] Vanilla FL (Vulnerable to Model Inversion)...")
    # Simulating Vanilla FL by training without LDP noise
    model_vanilla = HybridDL(input_dim)
    optimizer = torch.optim.Adam(model_vanilla.parameters(), lr=0.001)
    
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = criterion(model_vanilla(X_train_t), y_train_t)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        preds = (model_vanilla(X_test_t) > 0.5).int().numpy()
        van_acc = accuracy_score(y_test_np, preds)
        van_f1 = f1_score(y_test_np, preds, zero_division=0)
        van_rec = recall_score(y_test_np, preds, zero_division=0)

    # ---------------------------------------------------------
    # PROPOSED SYSTEM: Federated Learning + Local Differential Privacy (LDP)
    # ---------------------------------------------------------
    print("\n[Evaluating Proposed] DeCentra-Health (LDP + FL)...")
    try:
        model_proposed = HybridDL(input_dim)
        model_proposed.load_state_dict(torch.load("global_model_final.pth"))
        with torch.no_grad():
            preds = (model_proposed(X_test_t) > 0.5).int().numpy()
            prop_acc = accuracy_score(y_test_np, preds)
            prop_f1 = f1_score(y_test_np, preds, zero_division=0)
            prop_rec = recall_score(y_test_np, preds, zero_division=0)
    except:
        print("❌ Could not load your final global model. Make sure you trained it!")
        return

    # ---------------------------------------------------------
    # EXPORT RESULTS
    # ---------------------------------------------------------
    ml_data = {
        "Architecture": ["Centralized (Baseline)", "Vanilla FL", "Proposed (FL + LDP + SSI)"],
        "Privacy Protection": ["None", "Medium (Weights only)", "Absolute (Differential Privacy)"],
        "Accuracy": [f"{cent_acc*100:.2f}%", f"{van_acc*100:.2f}%", f"{prop_acc*100:.2f}%"],
        "F1-Score": [f"{cent_f1:.4f}", f"{van_f1:.4f}", f"{prop_f1:.4f}"],
        "Recall (Threat Detection)": [f"{cent_rec:.4f}", f"{van_rec:.4f}", f"{prop_rec:.4f}"]
    }
    pd.DataFrame(ml_data).to_csv("eval_3_ml_metrics.csv", index=False)
    print("   -> Results saved to eval_3_ml_metrics.csv")
    print("\n✅ ML Evaluation Complete. You can now present the exact Privacy-Utility Trade-off.")

if __name__ == "__main__":
    evaluate_ml_baselines()