## Commands reference

## Notes
- Always activate venv before running `uvicorn`.

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Run the API server
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### Test
Run the existing health and API test commands from this reference.
