import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

from sklearn.metrics import (
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_curve,
    auc
)

from fl_utils import HybridDL, preprocess_data


SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)


def evaluate_ml_metrics():

    print("\n" + "="*60)
    print("      FEDERATED LEARNING PERFORMANCE METRICS")
    print("="*60)

    # -------------------------------
    # LOAD DATA
    # -------------------------------

    if not all(os.path.exists(f"dataset_owner_{i}.csv") for i in [1,2,3]):
        print("Required datasets missing")
        return

    train_df = pd.concat([
        pd.read_csv("dataset_owner_1.csv"),
        pd.read_csv("dataset_owner_2.csv")
    ])

    test_df = pd.read_csv("dataset_owner_3.csv")

    X_train, y_train = preprocess_data(train_df)
    X_test, y_test = preprocess_data(test_df)

    print(f"\nDetected Input Features: {X_test.shape[1]}")
    print(f"Train Samples: {len(X_train)}")
    print(f"Test Samples: {len(X_test)}")

    # -------------------------------
    # TENSOR CONVERSION
    # -------------------------------

    X_train = torch.FloatTensor(np.array(X_train))
    y_train = torch.FloatTensor(np.array(y_train)).unsqueeze(1)

    X_test = torch.FloatTensor(np.array(X_test))
    y_test = torch.FloatTensor(np.array(y_test)).unsqueeze(1)

    y_test_np = y_test.numpy()

    # -------------------------------
    # LOAD GLOBAL MODEL
    # -------------------------------

    print("\n[Test 1] Evaluating Global Model (with Differential Privacy)")

    model_private = HybridDL(input_dim=X_test.shape[1])
    model_private.load_state_dict(torch.load("global_model_final.pth"))
    model_private.eval()

    with torch.no_grad():
        preds = model_private(X_test)
        probs = preds.numpy()
        preds_cls = (preds > 0.5).int().numpy()

    # -------------------------------
    # METRICS
    # -------------------------------

    cm = confusion_matrix(y_test_np, preds_cls)
    tn, fp, fn, tp = cm.ravel()

    acc_private = accuracy_score(y_test_np, preds_cls)
    precision = precision_score(y_test_np, preds_cls)
    recall = recall_score(y_test_np, preds_cls)
    f1 = f1_score(y_test_np, preds_cls)

    print(f"\nTP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
    print(f"Accuracy:  {acc_private*100:.2f}%")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")

    # -------------------------------
    # ROC CURVE
    # -------------------------------

    fpr, tpr, _ = roc_curve(y_test_np.ravel(), probs.ravel())
    roc_auc = auc(fpr, tpr)

    plt.figure()
    plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.3f}")
    plt.plot([0,1],[0,1],'r--')
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve - Federated IDS Model")
    plt.legend()
    plt.grid(True)
    plt.savefig("roc_curve.png")
    plt.show()

    # -------------------------------
    # BASELINE MODEL
    # -------------------------------

    print("\n[Test 2] Training Baseline Model (No Privacy)")

    model_baseline = HybridDL(input_dim=X_train.shape[1])
    optimizer = torch.optim.Adam(model_baseline.parameters(), lr=0.001)
    criterion = nn.BCELoss()

    for epoch in range(300):

        optimizer.zero_grad()
        outputs = model_baseline(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()

    model_baseline.eval()

    with torch.no_grad():
        preds_baseline = model_baseline(X_test)
        preds_baseline_cls = (preds_baseline > 0.5).int().numpy()

    acc_no_privacy = accuracy_score(y_test_np, preds_baseline_cls)

    print(f"Baseline Accuracy (No Privacy): {acc_no_privacy*100:.2f}%")

    # -------------------------------
    # FINAL REPORT
    # -------------------------------

    fl_accuracy = acc_private * 100
    baseline_accuracy = acc_no_privacy * 100
    utility_loss = baseline_accuracy - fl_accuracy

    print("\n" + "="*60)
    print("            FINAL IDS AI REPORT")
    print("="*60)

    print(f"\n1. Overall Accuracy")
    print(f"RESULT: {fl_accuracy:.2f}%")

    print(f"\n2. F1-Score (The Balanced Metric)")
    print(f"RESULT: {f1:.4f}")

    print(f"\n3. Recall (Sensitivity)")
    print(f"RESULT: {recall:.4f}")

    print(f"\n4. Privacy-Utility Trade-off (U_loss)")
    print(f"RESULT: {utility_loss:.2f}%")

    print("="*60)


if __name__ == "__main__":
    evaluate_ml_metrics()