"""Expose the FastAPI application for deployment.

This module simply re-exports the FastAPI application defined in
:mod:`app.main` so that running ``uvicorn facturx.api.main:app`` works as
expected.
"""

from __future__ import annotations

from app.main import app

__all__ = ["app"]
