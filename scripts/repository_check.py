#!/usr/bin/env python3
"""Check that the public repository contains no local runtime or obvious secrets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_HARNESS = ROOT / "src" / "jotta" / "templates" / ".jotta"
TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml", ".gitignore", ".gitattributes"}
SKIP_PARTS = {".git", "__pycache__", ".venv", "venv", "dist", "build"}
REQUIRED = {
    "README.md", "README.pt-BR.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md",
    "CHANGELOG.md", ".gitignore", ".gitattributes", "AGENTS.md", "CLAUDE.md", "pyproject.toml",
    ".github/workflows/validate.yml", "scripts/repository_check.py",
    "src/jotta/templates/AGENTS.md", "src/jotta/templates/CLAUDE.md", "src/jotta/templates/.jotta/config.yaml",
    "src/jotta/templates/.planning/PRD.md",
}


def public_files() -> list[Path]:
    return [path for path in ROOT.rglob("*") if path.is_file() and not (set(path.parts) & SKIP_PARTS)]


def main() -> int:
    errors: list[str] = []
    missing = sorted(path for path in REQUIRED if not (ROOT / path).exists())
    errors.extend(f"missing public repository file: {path}" for path in missing)

    runtime = TEMPLATE_HARNESS / "runtime"
    if runtime.exists() and any(runtime.rglob("*")):
        errors.append("template runtime contains local execution artifacts")

    for path in ROOT.rglob("*"):
        if path.is_file() and ("__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}):
            errors.append(f"Python cache present: {path.relative_to(ROOT)}")

    windows_user = re.compile(r"[A-Za-z]:" + re.escape("\\") + r"Users" + re.escape("\\") + r"[^\\\s]+", re.I)
    unix_user = re.compile(r"/(?:Users|home)/[^/\s]+")
    github_token = re.compile(r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{16,}")
    openai_style = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
    aws_key = re.compile(r"AKIA[0-9A-Z]{16}")
    bearer = re.compile(r"authorization\s*:\s*bearer\s+\S+", re.I)
    private_key = re.compile("-----BEGIN " + "PRIVATE KEY-----")
    patterns = [windows_user, unix_user, github_token, openai_style, aws_key, bearer, private_key]

    for path in public_files():
        relative = path.relative_to(ROOT)
        if path.name.startswith(".env") and path.name != ".env.example":
            errors.append(f"environment file present: {relative}")
        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            errors.append(f"key material present: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE", ".gitignore", ".gitattributes"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "\u2013" in text or "\u2014" in text:
            errors.append(f"forbidden dash character: {relative}")
        for pattern in patterns:
            if pattern.search(text):
                errors.append(f"sensitive pattern {pattern.pattern!r}: {relative}")
                break
        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON {relative}: {exc}")

    if (TEMPLATE_HARNESS / "state").exists():
        errors.append("templates must not ship execution state; it is created under runtime/state")
    ignore = TEMPLATE_HARNESS / ".gitignore"
    if not ignore.exists() or "runtime/" not in ignore.read_text(encoding="utf-8").splitlines():
        errors.append("template .jotta/.gitignore must ignore runtime/")

    if errors:
        print("REPOSITORY CHECK FAILED")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 1
    print(f"REPOSITORY CHECK OK: {len(public_files())} files inspected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
