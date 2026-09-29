# Week 5, Day 1 — Classical ML Foundations: Regression + Train/Val/Test

## 1. What is regression?
Regression predicts a continuous number (e.g., diabetes progression) rather than a category. We fit a line (or curve) so the model minimizes the gap between predictions and true values.

## 2. Why shouldn't the test set be used while developing the model?
If we tune using the test set, we leak information from the final evaluation into training. The test score becomes optimistic and no longer reflects true generalization to unseen data.

## 3. What is the purpose of validation data?
Validation provides a neutral checkpoint during development. We use it to compare model choices, catch overfitting early, and decide hyperparameters before the one-time final evaluation on the test set.

## 4. What would it mean if train MAE = 2 and validation MAE = 25?
The model fits training examples very closely but fails on new data. This is overfitting: it captures noise and idiosyncrasies of the training set instead of the underlying pattern.

## 5. What would it mean if train MAE = 18 and validation MAE = 19?
Performance is similar across splits. The model generalizes; it has not overfit and is not severely underfitting. The gap is small, so training and validation estimates are consistent.

## 6. Why is the test score not something we repeatedly optimize against?
Repeated optimization against the test set turns it into a hidden validation set. The final score stops measuring true out-of-sample performance and starts measuring how well we tuned to that specific split.

## Overfitting explanation (not just "memorizes")
Overfitting means the model learns the specific noise, outliers, and sampling artifacts of the training distribution, not the generalizable signal. It produces a very complex decision surface that happens to match training points closely but deviates sharply on new samples, causing a large train/validation gap.
