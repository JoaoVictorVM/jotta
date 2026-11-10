#!/usr/bin/env python3
"""Compatibility wrapper for `jotta models`."""

from _jotta_shim import run

raise SystemExit(run("models"))
