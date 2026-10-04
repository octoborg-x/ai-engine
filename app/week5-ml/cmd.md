# Week 5 ML — How to run

## Setup (virtual env + dependencies)
```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# Windows: .venv\Scripts\activate
python -m pip install scikit-learn numpy
```

## Run regression experiment
```bash
source app/week5/.venv/bin/activate
python app/week5/regression.py
```

Or directly (no activate):
```bash
app/week5/.venv/bin/python app/week5/regression.py
```

Expected output: Train MAE, Validation MAE, Test MAE printed.
