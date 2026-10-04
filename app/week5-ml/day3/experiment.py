"""
Week 5, Day 3 — Evaluation, Overfitting, Regularization, Classification Metrics

Experiment:
- Train/validation/test split
- Sequence of model complexities (underfit → good fit → overfit)
- Regularization comparison
- Precision / Recall / F1 / ROC-AUC
- Accuracy misleading on imbalanced data
"""

import numpy as np
from sklearn.datasets import make_classification
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


# ------------------------------------------------------------------
# Helper to evaluate
# ------------------------------------------------------------------
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,invalid-name
def evaluate(name, model, X_tr, y_tr, X_va, y_va, X_te, y_te):
    """Fit model and calculate evaluation metrics across train/val/test splits."""
    model.fit(X_tr, y_tr)
    preds_va = model.predict(X_va)
    preds_te = model.predict(X_te)
    probs_va = (
        model.predict_proba(X_va)[:, 1] if hasattr(model, "predict_proba") else None
    )
    probs_te = (
        model.predict_proba(X_te)[:, 1] if hasattr(model, "predict_proba") else None
    )

    # Confusion matrix on validation
    cm = confusion_matrix(y_va, preds_va)
    if cm.size == 4:
        tn, fp, fn, tp = cm.ravel()
        print(f"    CM: TP={tp} FP={fp} FN={fn} TN={tn}")

    def metrics(y_true, y_pred, probs=None):
        return {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1": f1_score(y_true, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_true, probs) if probs is not None else None,
        }

    m_train = metrics(
        y_tr,
        model.predict(X_tr),
        model.predict_proba(X_tr)[:, 1] if hasattr(model, "predict_proba") else None,
    )
    m_val = metrics(y_va, preds_va, probs_va)
    m_test = metrics(y_te, preds_te, probs_te)

    return {
        "name": name,
        "train_f1": m_train["f1"],
        "val_f1": m_val["f1"],
        "test_f1": m_test["f1"],
        "train_acc": m_train["accuracy"],
        "val_acc": m_val["accuracy"],
        "test_acc": m_test["accuracy"],
        "val_precision": m_val["precision"],
        "val_recall": m_val["recall"],
        "val_roc_auc": m_val["roc_auc"],
        "test_roc_auc": m_test["roc_auc"],
        "cm": cm,
        "model": model,
    }


# pylint: disable=too-many-locals
def main():
    """Run model complexity and evaluation comparison experiment."""
    np.random.seed(42)

    # ------------------------------------------------------------------
    # 1. Dataset — imbalanced so accuracy can be misleading
    # ------------------------------------------------------------------
    x_data, y_data = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=10,
        n_redundant=5,
        n_classes=2,
        weights=[0.85, 0.15],
        flip_y=0.02,
        random_state=42,
    )

    # Split: train / validation / test
    x_trainval, x_test, y_trainval, y_test = train_test_split(
        x_data, y_data, test_size=0.20, stratify=y_data, random_state=42
    )
    x_train, x_val, y_train, y_val = train_test_split(
        x_trainval, y_trainval, test_size=0.25, stratify=y_trainval, random_state=42
    )

    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_val_s = scaler.transform(x_val)
    x_test_s = scaler.transform(x_test)

    # ------------------------------------------------------------------
    # 2. Model sequence — increasing complexity
    # ------------------------------------------------------------------
    results = []

    # Simple: linear with strong regularization (underfit tendency)
    results.append(
        evaluate(
            "Simple (LR C=0.01)",
            LogisticRegression(C=0.01, max_iter=1000),
            x_train_s,
            y_train,
            x_val_s,
            y_val,
            x_test_s,
            y_test,
        )
    )

    # Medium: logistic with moderate C
    results.append(
        evaluate(
            "Medium (LR C=1)",
            LogisticRegression(C=1, max_iter=1000),
            x_train_s,
            y_train,
            x_val_s,
            y_val,
            x_test_s,
            y_test,
        )
    )

    # Complex: deep tree (high variance / overfit)
    results.append(
        evaluate(
            "Complex (Tree depth=20)",
            DecisionTreeClassifier(max_depth=20, random_state=42),
            x_train_s,
            y_train,
            x_val_s,
            y_val,
            x_test_s,
            y_test,
        )
    )

    # Complex + regularization: tree with strong constraints (low variance)
    results.append(
        evaluate(
            "Complex+Reg (Tree d=3)",
            DecisionTreeClassifier(max_depth=3, min_samples_leaf=10, random_state=42),
            x_train_s,
            y_train,
            x_val_s,
            y_val,
            x_test_s,
            y_test,
        )
    )

    # ------------------------------------------------------------------
    # 3. Print results
    # ------------------------------------------------------------------
    print("=" * 70)
    header = (
        f"{'Model':<25} {'Train F1':>9} {'Val F1':>9} {'Test F1':>9}  "
        f"{'Val Acc':>8} {'Test Acc':>9}"
    )
    print(header)
    print("=" * 70)
    for r in results:
        line = (
            f"{r['name']:<25} {r['train_f1']:>9.3f} {r['val_f1']:>9.3f} "
            f"{r['test_f1']:>9.3f}  {r['val_acc']:>8.3f} {r['test_acc']:>9.3f}"
        )
        print(line)

    print()
    print("Confusion matrices (Validation):")
    for r in results:
        cm = r["cm"]
        if cm.size == 4:
            tn, fp, fn, tp = cm.ravel()
            print(f"  {r['name']:25s}  TP={tp} FP={fp} FN={fn} TN={tn}")

    print()
    print("Precision / Recall / F1 / ROC-AUC (Validation):")
    for r in results:
        metrics_line = (
            f"  {r['name']:25s}  P={r['val_precision']:.3f}  "
            f"R={r['val_recall']:.3f}  F1={r['val_f1']:.3f}  "
            f"AUC={r['val_roc_auc']:.3f}"
        )
        print(metrics_line)

    # ------------------------------------------------------------------
    # 4. Demonstrate misleading accuracy on imbalanced data
    # ------------------------------------------------------------------
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(x_train_s, y_train)
    dummy_acc = accuracy_score(y_val, dummy.predict(x_val))
    dummy_recall = recall_score(y_val, dummy.predict(x_val), zero_division=0)
    print()
    print("IMBALANCED DATA — ACCURACY MISLEADING:")
    print(f"  Majority-class dummy accuracy = {dummy_acc:.3f} ({dummy_acc * 100:.1f}%)")
    print(
        f"  Majority-class dummy recall    = {dummy_recall:.3f} (catches 0 positives)"
    )
    print("  → High accuracy, zero useful signal. Don't optimize accuracy blindly.")


if __name__ == "__main__":
    main()
