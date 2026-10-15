# Classical ML training and inference

This package keeps the final end-to-end PyTorch binary-classification pipeline
as one runnable feature: deterministic synthetic data, train/validation split,
training loop, best-checkpoint selection, CSV metrics, and inference.

## Components

- `data.py`: seeded tabular dataset and reproducible loaders.
- `model.py`: configurable binary classifier.
- `train.py`: training, validation, checkpointing, and metric logging.
- `inference.py`: loads the best checkpoint and predicts on new examples.
- `regression.py`: classical regression baseline.
- `checkpoints/best.pt`: example trained checkpoint.
- `results/`: recorded metric runs.

## Run

Requires the optional PyTorch dependency. Run from the repository root as a
module so package imports resolve consistently:

```bash
python -m app.ml.train
python -m app.ml.inference
```

Training writes metrics to `app/ml/results/metrics.csv` and the best model to
`app/ml/checkpoints/best.pt`. The checkpoint is selected using validation
accuracy, not the final epoch. The dataset and split use fixed seeds to make
experiments reproducible.
