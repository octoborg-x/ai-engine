# Week 5 — Day 3: Evaluation + Overfitting

## Mental Model

```
Dataset
    │
    ├─→ Training  → fit parameters
    │
    ├─→ Validation → choose complexity / regularize
    │
    └─→ Test       → final estimate of generalization
```

**Overfitting** = good on train, bad on unseen.
**Underfitting** = too simple to capture signal.
**Regularization** = deliberately constrain complexity to improve generalization.

---

## Experiment (`experiment.py`)

Uses `sklearn.datasets.make_classification` (85% negative / 15% positive, 1000 samples).
Train / validation / test split with `stratify=y` to preserve class ratios.

### Model progression

| Model | Complexity | Intent |
|---|---|---|
| Simple (LR C=0.01) | Low | Underfit — high regularization, cannot learn minority class |
| Medium (LR C=1) | Medium | Good generalization — best validation F1 |
| Complex (Tree d=20) | High | Overfit — train F1=1.000, test F1=0.386 (big gap) |
| Complex+Reg (Tree d=3) | High + constrained | Regularized — smaller gap, more stable test F1 |

### Results (from run)

| Model | Train F1 | Val F1 | Test F1 | Val Acc | Test Acc |
|---|---|---|---|---|---|
| Simple (LR C=0.01) | 0.040 | 0.000 | 0.000 | 0.840 | 0.840 |
| Medium (LR C=1) | 0.559 | 0.604 | 0.655 | 0.895 | 0.905 |
| Complex (Tree d=20) | **1.000** | 0.627 | **0.386** | 0.875 | 0.825 |
| Complex+Reg (Tree d=3) | 0.648 | 0.603 | 0.400 | 0.875 | 0.835 |

**Where overfitting begins:** the deep tree (d=20) memorizes training noise; validation F1 is decent but test F1 collapses — the gap between train and test is the generalization gap.

**Regularization effect:** constraining depth to 3 and requiring `min_samples_leaf=10` shrinks the train/test gap (train 0.648 → test 0.400) vs the unconstrained tree (1.000 → 0.386). Regularization trades some training performance for more stable generalization.

---

## Metrics Explained

Confusion matrix:

```
Predicted
          Pos     Neg
Actual Pos  TP     FN
Actual Neg  FP     TN
```

- **Precision** = TP / (TP + FP) — "When I say positive, how often am I right?"
- **Recall** = TP / (TP + FN) — "Of all actual positives, how many did I catch?"
- **F1** = 2·P·R / (P+R) — balances precision and recall.
- **ROC-AUC** — measures ranking quality across thresholds (1.0 = perfect separation; 0.5 = random).

---

## Why Accuracy Can Be Misleading

Dataset is imbalanced (~85% negative). A dummy classifier that predicts the majority class every time achieves:

- **Accuracy = 84.0%**
- **Recall = 0.000** (catches zero positives)

This is the engineering reason you don't blindly optimize accuracy. When positives are rare and costly to miss, accuracy hides failure.

**Business failure mode mapping:**

- **High cost of false positive** (e.g., spam filter flagging real email) → optimize **Precision**.
- **High cost of false negative** (e.g., fraud, disease screening) → optimize **Recall**.
- **Need both** → optimize **F1** or use **ROC-AUC** / PR-AUC depending on class balance.

---

## Why Test Set Should Not Drive Model Selection

The test set must remain untouched during model selection. If we choose hyperparameters (depth, C, regularization) based on test performance, we leak information into the model — the test becomes a validation set, and our "final estimate" of generalization is over-optimistic. The split is:

1. **Train** — fit parameters.
2. **Validation** — compare models, pick complexity / regularization.
3. **Test** — one-time final evaluation.

---

## Running

```bash
python week5/day3/experiment.py
```

Requires: `scikit-learn`, `numpy`.

---

## Done Checklist

- [x] Correct train/validation/test split (stratified)
- [x] Can explain why test set should not drive model selection
- [x] Demonstrated underfitting / overfitting experimentally
- [x] Demonstrated regularization (constrained tree vs deep tree)
- [x] Can calculate / explain precision, recall, F1
- [x] Can explain ROC-AUC
- [x] Can identify when accuracy is inappropriate (imbalanced dummy)
- [x] Results documented in README.md
- [x] Code runs reproducibly (seed=42, fixed split)
