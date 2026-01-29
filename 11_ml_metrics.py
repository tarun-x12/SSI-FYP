import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, accuracy_score
from fl_utils import HybridDL, preprocess_data, generate_dummy_data

def evaluate_ml_metrics():
    print("\n" + "="*60)
    print("      🧠  FEDERATED LEARNING PERFORMANCE METRICS      ")
    print("="*60)

    # --- 1. PREPARE TEST DATA ---
    print("\n[Setup] Generating standardized Test Set...")
    # We generate a clean test set (not seen during training)
    test_df = generate_dummy_data(rows=200)
    X_test, y_test = preprocess_data(test_df)
    
    # Convert to Tensor
    X_test_tensor = torch.FloatTensor(X_test)
    y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1)

    # --- 2. EVALUATE GLOBAL MODEL (WITH PRIVACY) ---
    print("[Test 1] Evaluating Global Model (with Differential Privacy)...")
    
    try:
        # Load the model structure
        model_private = HybridDL(input_dim=X_test.shape[1])
        
        # Load the trained weights
        state_dict = torch.load("global_model_final.pth")
        model_private.load_state_dict(state_dict)
        model_private.eval()

        # Predict
        with torch.no_grad():
            preds_private = model_private(X_test_tensor)
            preds_private_cls = (preds_private > 0.5).float()
        
        # Calculate Accuracy Components
        tn, fp, fn, tp = confusion_matrix(y_test, preds_private_cls).ravel()
        acc_private = accuracy_score(y_test, preds_private_cls)

        print(f"   ✅ Global Model Loaded.")
        print(f"   TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
        print(f"   Accuracy (Private): {acc_private * 100:.2f}%")

    except FileNotFoundError:
        print("❌ Error: 'global_model_final.pth' not found.")
        print("   Run '4_analyst_persistent.py' first to aggregate a model.")
        return

    # --- 3. TRAIN BASELINE MODEL (NO PRIVACY) ---
    print("\n[Test 2] Training Baseline Model (No Privacy) for Comparison...")
    # We simulate a model trained on raw data WITHOUT LDP noise
    
    # Generate clean training data
    train_df = generate_dummy_data(rows=500)
    X_train, y_train = preprocess_data(train_df)
    
    # Note: We skip 'apply_ldp' here to get the "No-Privacy" benchmark
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)

    model_baseline = HybridDL(input_dim=X_train.shape[1])
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model_baseline.parameters(), lr=0.01)

    # Fast Training Loop
    model_baseline.train()
    for epoch in range(10):
        optimizer.zero_grad()
        output = model_baseline(X_train_tensor)
        loss = criterion(output, y_train_tensor)
        loss.backward()
        optimizer.step()

    # Evaluate Baseline
    model_baseline.eval()
    with torch.no_grad():
        preds_baseline = model_baseline(X_test_tensor)
        preds_baseline_cls = (preds_baseline > 0.5).float()
    
    acc_no_privacy = accuracy_score(y_test, preds_baseline_cls)
    print(f"   ✅ Baseline Trained.")
    print(f"   Accuracy (No Privacy): {acc_no_privacy * 100:.2f}%")


    # --- 4. CALCULATE FINAL METRICS ---
    
    # 4.5 Federated Learning Accuracy
    fl_accuracy = acc_private * 100

    # 4.6 Privacy-Utility Trade-off
    # U_loss = Acc_no_privacy - Acc_private
    utility_loss = (acc_no_privacy - acc_private) * 100

    print("\n" + "="*60)
    print("      📈  FINAL ML PERFORMANCE REPORT      ")
    print("="*60)
    
    print(f"4.5 Federated Learning Accuracy")
    print(f"   Formula: (TP + TN) / (TP + TN + FP + FN)")
    print(f"   RESULT: {fl_accuracy:.2f}%")
    print(f"   (Accuracy of the secure, aggregated global model)")

    print(f"\n4.6 Privacy-Utility Trade-off (U_loss)")
    print(f"   Formula: Acc_no-privacy - Acc_private")
    print(f"   RESULT: {utility_loss:.2f}%")
    print(f"   (Accuracy drop caused by adding Differential Privacy)")
    
    if utility_loss < 5.0:
        print("   ✅ CONCLUSION: High Utility Preserved (Low Loss).")
    else:
        print("   ⚠️ CONCLUSION: Privacy noise significantly impacted accuracy.")

    print("="*60 + "\n")

if __name__ == "__main__":
    evaluate_ml_metrics()