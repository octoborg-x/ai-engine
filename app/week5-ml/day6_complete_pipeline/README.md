# Complete PyTorch Pipeline (Week 5, Day 6)

Files:
- model.py: BinaryClassifier (configurable hidden size)
- data.py: TabularDataset + loaders (80/20 split, seed=42)
- train.py: full loop with train/eval, validation, checkpointing, CSV log
- inference.py: load best.pt, model.eval(), predict unseen data, human-readable output
- checkpoints/best.pt: saved when val_accuracy improves

Key concepts:
- model.train() enables dropout/batchnorm updates; model.eval() disables them.
- Validation uses torch.no_grad() and must not call optimizer.step() or loss.backward().
- Best checkpoint saved by validation metric, not last epoch, to avoid overfitting deployment.
- Metrics recorded: epoch, train_loss, validation_loss, validation_metric (accuracy).

Experiments compared:
- Exp1: lr=0.05, hidden=16 -> best val_acc 1.00 (fast convergence)
- Exp3: lr=0.01, hidden=16 -> best val_acc 0.85 (slower learning, underfits at 20 epochs)
Why: higher lr allows faster descent into loss minimum; lower lr still learning at epoch 20.

Run: python train.py (produces metrics.csv + checkpoints/best.pt) then python inference.py
