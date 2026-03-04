import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import os

from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from fl_utils import HybridDL, preprocess_data

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)


def evaluate_ml_metrics():

    print("\n" + "="*60)
    print("      FEDERATED LEARNING PERFORMANCE METRICS")
    print("="*60)

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    if not (
        os.path.exists("dataset_owner_1.csv") and
        os.path.exists("dataset_owner_2.csv") and
        os.path.exists("dataset_owner_3.csv")
    ):
        print("❌ Required datasets not found")
        return

    print("[Setup] Using Owner 1 + Owner 2 for training")
    print("[Setup] Using Owner 3 for testing")

    train_df = pd.concat([
        pd.read_csv("dataset_owner_1.csv"),
        pd.read_csv("dataset_owner_2.csv")
    ])

    test_df = pd.read_csv("dataset_owner_3.csv")

    X_train, y_train = preprocess_data(train_df)
    X_test, y_test = preprocess_data(test_df)

    print(f"Detected Input Features: {X_test.shape[1]}")
    print(f"Train Samples: {len(X_train)}")
    print(f"Test Samples: {len(X_test)}")

    # --------------------------------------------------
    # NUMPY FIX
    # --------------------------------------------------

    X_train = np.array(X_train).copy()
    X_test = np.array(X_test).copy()

    y_train = np.array(y_train).astype(int).copy()
    y_test = np.array(y_test).astype(int).copy()

    # --------------------------------------------------
    # TENSOR CONVERSION
    # --------------------------------------------------

    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)

    X_test_tensor = torch.FloatTensor(X_test)
    y_test_tensor = torch.FloatTensor(y_test).unsqueeze(1)

    # --------------------------------------------------
    # LOAD GLOBAL MODEL
    # --------------------------------------------------

    print("\n[Test 1] Evaluating Global Federated Model...")

    try:

        model_private = HybridDL(input_dim=X_test.shape[1])

        state_dict = torch.load("global_model_final.pth")

        model_private.load_state_dict(state_dict)

        model_private.eval()

        with torch.no_grad():

            preds_private = model_private(X_test_tensor)

            preds_private_cls = (preds_private > 0.5).int().numpy()

    except FileNotFoundError:

        print("❌ global_model_final.pth not found")

        return

    # --------------------------------------------------
    # METRICS
    # --------------------------------------------------

    y_test_np = y_test_tensor.numpy()

    cm = confusion_matrix(y_test_np, preds_private_cls)

    print("\nConfusion Matrix:")
    print(cm)

    if cm.shape != (2, 2):
        print("❌ Dataset not binary classification")
        return

    tn, fp, fn, tp = cm.ravel()

    acc_private = accuracy_score(y_test_np, preds_private_cls)
    precision = precision_score(y_test_np, preds_private_cls, zero_division=0)
    recall = recall_score(y_test_np, preds_private_cls, zero_division=0)
    f1 = f1_score(y_test_np, preds_private_cls, zero_division=0)

    print("\nGlobal Model Loaded.")
    print(f"TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")

    print(f"Accuracy:  {acc_private*100:.2f}%")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")

    # --------------------------------------------------
    # BASELINE MODEL
    # --------------------------------------------------

    print("\n[Test 2] Training Baseline Model (No Privacy)...")

    model_baseline = HybridDL(input_dim=X_train.shape[1])

    criterion = nn.BCELoss()

    optimizer = torch.optim.Adam(model_baseline.parameters(), lr=0.001)

    model_baseline.train()

    for epoch in range(300):

        optimizer.zero_grad()

        outputs = model_baseline(X_train_tensor)

        loss = criterion(outputs, y_train_tensor)

        loss.backward()

        optimizer.step()

    model_baseline.eval()

    with torch.no_grad():

        preds_baseline = model_baseline(X_test_tensor)

        preds_baseline_cls = (preds_baseline > 0.5).int().numpy()

    acc_no_privacy = accuracy_score(y_test_np, preds_baseline_cls)

    print("Baseline Trained.")
    print(f"Accuracy (No Privacy): {acc_no_privacy*100:.2f}%")

    # --------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------

    fl_accuracy = acc_private * 100
    utility_loss = (acc_no_privacy - acc_private) * 100

    print("\n" + "="*60)
    print("      FINAL INTRUSION DETECTION AI REPORT")
    print("="*60)

    print(f"1. Overall Accuracy")
    print(f"RESULT: {fl_accuracy:.2f}%")

    print(f"\n2. F1 Score")
    print(f"RESULT: {f1:.4f}")

    print(f"\n3. Recall (Sensitivity)")
    print(f"RESULT: {recall:.4f}")

    print(f"\n4. Privacy-Utility Trade-off")
    print(f"RESULT: {utility_loss:.2f}%")

    print("="*60)


if __name__ == "__main__":

    evaluate_ml_metrics()