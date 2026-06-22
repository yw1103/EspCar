"""Shared pytest fixtures for the orchestrator test suite."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make ``deskcar_orch`` importable without an install.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402