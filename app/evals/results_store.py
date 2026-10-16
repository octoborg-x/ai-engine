"""Persisted evaluation results for the console.

Real comparison/eval runs are expensive (they call the LLM provider for every
case). To keep the dashboard cheap and avoid exhausting the server, every
successful run can be saved here as JSON. The console's "fake run" path reads
these files directly (no backend LLM call) and the dashboard shows them by
default until a user explicitly requests a fresh run.

Layout (kept in the repo so builds ship them):
    web/public/results/<tab>-example-<n>.json   n in 1..3   (frontend statics)
    app/evals/seed_results/<tab>-example-<n>.json            (backend fallback)

The store writes new results to the writable directory (``RESULTS_DIR`` env,
or ``web/public/results`` in a monorepo checkout) and falls back to the
bundled seed files when the checkout is absent — e.g. a deployed backend
container that only ships ``app/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# How many saved runs the console rotates through per tab.
SLOTS = 3

# Tabs that have a persisted result artifact.
TABS = ("compare", "evals", "retrieval")

_PREFIX = "example"


def _results_dir() -> Path:
    """Writable directory where the console's saved results live."""
    override = os.getenv("RESULTS_DIR")
    if override:
        return Path(override)
    repo_root = Path(__file__).resolve().parents[2]  # repo root
    return repo_root / "web" / "public" / "results"


def _seed_dir() -> Path:
    """Read-only seed results bundled inside the Python package."""
    return Path(__file__).resolve().parent / "seed_results"


def results_dir() -> str:
    return str(_results_dir())


def _ensure_dir() -> Path:
    root = _results_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(tab: str, slot: int) -> Path:
    return _ensure_dir() / f"{tab}-{_PREFIX}-{slot}.json"


def _slots_from(directory: Path, tab: str) -> list[int]:
    return [
        n
        for n in range(1, SLOTS + 1)
        if (directory / f"{tab}-{_PREFIX}-{n}.json").exists()
        and (directory / f"{tab}-{_PREFIX}-{n}.json").stat().st_size > 0
    ]


def _read_payload(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_results() -> dict[str, list[dict]]:
    """Index of saved results per tab, newest slot first."""
    index: dict[str, list[dict]] = {}
    for tab in TABS:
        entries = []
        for slot in reversed(_slots_from(_results_dir(), tab)):
            entries.append(
                {
                    "tab": tab,
                    "slot": slot,
                    "key": f"{tab}-{_PREFIX}-{slot}",
                    "url": f"/results/{tab}-{_PREFIX}-{slot}.json",
                    "timestamp": _path(tab, slot).stat().st_mtime,
                }
            )
        index[tab] = entries
    return index


def load_result(tab: str, slot: int | None = None) -> dict | None:
    """Return the saved result for a tab.

    ``slot`` selects a specific saved run; the default picks the most recent
    one. Writable results win over the bundled seeds. Returns ``None`` when
    nothing is saved yet.
    """
    if tab not in TABS:
        return None
    for directory in (_results_dir(), _seed_dir()):
        slots = _slots_from(directory, tab)
        if not slots:
            continue
        chosen = slot if slot in slots else slots[-1]
        payload = _read_payload(directory / f"{tab}-{_PREFIX}-{chosen}.json")
        if payload is None:
            continue
        payload.setdefault("_meta", {}).update(
            {
                "tab": tab,
                "slot": chosen,
                "key": f"{tab}-{_PREFIX}-{chosen}",
                "path": str(directory),
            }
        )
        return payload
    return None


def save_result(tab: str, payload: dict) -> dict:
    """Persist a run result into the next free slot (newest wins)."""
    if tab not in TABS:
        raise ValueError(f"unknown results tab: {tab}")
    used = _slots_from(_results_dir(), tab)
    slot = min((n for n in range(1, SLOTS + 1) if n not in used), default=1)
    path = _path(tab, slot)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "tab": tab,
        "slot": slot,
        "key": f"{tab}-{_PREFIX}-{slot}",
        "path": str(path),
    }
