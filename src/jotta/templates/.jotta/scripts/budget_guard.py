#!/usr/bin/env python3
"""Compatibility wrapper for `jotta budget`."""

from _jotta_shim import run

raise SystemExit(run("budget"))
