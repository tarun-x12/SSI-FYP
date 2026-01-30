import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import os
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from fl_utils import HybridDL, preprocess_data, generate_dummy_data

def evaluate_ml_metrics():
    print("\n" + "="*60)
    print("      🧠  FEDERATED LEARNING PERFORMANCE METRICS      ")
    print("="*60)

    # --- 1. DETERMINE INPUT SHAPE ---
    if os.path.exists("dataset_owner_1.csv"):
        print("[Setup] Detected Real Data. Loading sample to determine shape...")
        df_sample = pd.read_csv("dataset_owner_1.csv")
        test_df = df_sample.sample(frac=0.2, random_state=42) 
        X_test, y_test = preprocess_data(test_df)
        print(f"   > Detected Input Features: {X_test.shape[1]}")
    else:
        print("[Setup] No Real Data found. Falling back to Dummy Data...")
        test_df = generate_dummy_data(rows=200)
        X_test, y_test = preprocess_data(test_df)

    # Convert to Tensor
    X_test_tensor = torch.FloatTensor(X_test)
    y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1)

    # --- 2. EVALUATE GLOBAL MODEL (WITH PRIVACY) ---
    print("\n[Test 1] Evaluating Global Model (with Differential Privacy)...")
    
    try:
        model_private = HybridDL(input_dim=X_test.shape[1])
        state_dict = torch.load("global_model_final.pth")
        model_private.load_state_dict(state_dict)
        model_private.eval()

        with torch.no_grad():
            preds_private = model_private(X_test_tensor)
            preds_private_cls = (preds_private > 0.5).float()
        
        # --- NEW METRICS CALCULATION ---
        tn, fp, fn, tp = confusion_matrix(y_test, preds_private_cls).ravel()
        acc_private = accuracy_score(y_test, preds_private_cls)
        precision = precision_score(y_test, preds_private_cls, zero_division=0)
        recall = recall_score(y_test, preds_private_cls, zero_division=0)
        f1 = f1_score(y_test, preds_private_cls, zero_division=0)

        print(f"   ✅ Global Model Loaded.")
        print(f"   TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
        print(f"   Accuracy:  {acc_private * 100:.2f}%")
        print(f"   Precision: {precision:.4f}")
        print(f"   Recall:    {recall:.4f}")
        print(f"   F1-Score:  {f1:.4f}")

    except FileNotFoundError:
        print("❌ Error: 'global_model_final.pth' not found.")
        return
    except RuntimeError as e:
        print(f"❌ Shape Mismatch: {e}")
        return

    # --- 3. TRAIN BASELINE MODEL (NO PRIVACY) ---
    print("\n[Test 2] Training Baseline Model (No Privacy) for Comparison...")
    
    if os.path.exists("dataset_owner_1.csv"):
        train_df = pd.read_csv("dataset_owner_1.csv").sample(frac=0.8, random_state=42)
    else:
        train_df = generate_dummy_data(rows=500)

    X_train, y_train = preprocess_data(train_df)
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)

    model_baseline = HybridDL(input_dim=X_train.shape[1])
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model_baseline.parameters(), lr=0.01)

    model_baseline.train()
    for epoch in range(100): 
        optimizer.zero_grad()
        output = model_baseline(X_train_tensor)
        loss = criterion(output, y_train_tensor)
        loss.backward()
        optimizer.step()

    model_baseline.eval()
    with torch.no_grad():
        preds_baseline = model_baseline(X_test_tensor)
        preds_baseline_cls = (preds_baseline > 0.5).float()
    
    acc_no_privacy = accuracy_score(y_test, preds_baseline_cls)
    print(f"   ✅ Baseline Trained.")
    print(f"   Accuracy (No Privacy): {acc_no_privacy * 100:.2f}%")


    # --- 4. CALCULATE FINAL REPORT ---
    fl_accuracy = acc_private * 100
    utility_loss = (acc_no_privacy - acc_private) * 100

    print("\n" + "="*60)
    print("      📈  FINAL MEDICAL AI REPORT      ")
    print("="*60)
    
    print(f"1. Overall Accuracy")
    print(f"   RESULT: {fl_accuracy:.2f}%")
    print(f"   (Correct predictions / Total Cases)")

    print(f"\n2. F1-Score (The Balanced Metric)")
    print(f"   RESULT: {f1:.4f}")
    print(f"   (Harmonic mean of Precision and Recall. Max is 1.0)")
    
    print(f"\n3. Recall (Sensitivity)")
    print(f"   RESULT: {recall:.4f}")
    print(f"   (Ability to detect positive cases)")

    print(f"\n4. Privacy-Utility Trade-off (U_loss)")
    print(f"   RESULT: {utility_loss:.2f}%")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    evaluate_ml_metrics()