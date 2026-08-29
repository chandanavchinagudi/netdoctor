#!/usr/bin/env python3
"""
NetDoctor – Local History Storage
Stores previous diagnosis results as JSON files.
Pure standard library only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


# Directory where history files will be saved
HISTORY_DIR = Path("history_data")


def _ensure_history_dir() -> None:
    """Create the history directory if it doesn't exist."""
    HISTORY_DIR.mkdir(exist_ok=True)


def save_result(target: str, results_data: Dict[str, Any]) -> str:
    """
    Save a diagnosis result to a JSON file.
    
    Returns the filename that was created.
    """
    _ensure_history_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean target name for filename (remove special characters)
    safe_target = "".join(c if c.isalnum() or c in "-." else "_" for c in target)
    filename = f"{timestamp}_{safe_target}.json"
    filepath = HISTORY_DIR / filename

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "target": target,
        "data": results_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return str(filepath)


def list_history(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Return the most recent history entries (newest first).
    """
    _ensure_history_dir()

    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    entries = []

    for file in files[:limit]:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                entries.append({
                    "file": str(file),
                    "timestamp": data.get("timestamp"),
                    "target": data.get("target"),
                    "score": data.get("data", {}).get("health", {}).get("score"),
                    "grade": data.get("data", {}).get("health", {}).get("grade"),
                })
        except Exception:
            continue

    return entries


def load_result(filepath: str) -> Optional[Dict[str, Any]]:
    """Load a specific history file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_history() -> int:
    """Delete all history files. Returns number of files deleted."""
    _ensure_history_dir()
    count = 0
    for file in HISTORY_DIR.glob("*.json"):
        try:
            file.unlink()
            count += 1
        except Exception:
            pass
    return count