#!/usr/bin/env python3
"""Compatibility wrapper for `jotta orca`."""

from _jotta_shim import run

raise SystemExit(run("orca"))
