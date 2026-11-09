#!/usr/bin/env python3
"""Compatibility wrapper for `jotta`."""

from _jotta_shim import run

raise SystemExit(run())
