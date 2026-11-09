"""Run configured quality commands and emit bounded receipts."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, print_json

EXIT_INVALID_PROFILE = 2
ERROR_LINE = re.compile(r"(?i)(error|failed|failure|exception|traceback|assert|expected|fatal|\bE\d{3,}\b)")


def compact(text: str, limit: int = 40) -> list[str]:
    """Keep the lines most likely to explain a failure, announcing what was omitted."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if ERROR_LINE.search(line) and line not in seen:
            selected.append(line[:500])
            seen.add(line)
            if len(selected) >= limit:
                break
    if not selected:
        selected = [line[:500] for line in lines[-min(limit, len(lines)) :]]
    if len(lines) > len(selected) and limit > 0:
        marker = f"... {len(lines) - len(selected)} lines omitted; see log_path in the receipt"
        if len(selected) >= limit:
            selected[-1] = marker
        else:
            selected.append(marker)
    return selected


def run_profile(paths: ProjectPaths, profile: str, max_lines: int = 40) -> int:
    """Run every command of a quality profile and write a compact receipt."""
    data = load_json(paths.gates)
    profiles = data.get("profiles", {})
    if profile not in profiles:
        print_json({"status": "invalid", "profile": profile}, indent=None)
        return EXIT_INVALID_PROFILE

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = paths.runtime / "logs" / stamp
    receipt_dir = paths.runtime / "receipts"
    log_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[JSONDict] = []
    final_code = 0

    commands = profiles[profile]
    result: JSONDict
    if not commands:
        result = {"status": "skipped", "profile": profile, "reason": "no commands configured", "commands": []}
    else:
        for index, command in enumerate(commands, 1):
            process = subprocess.run(command, cwd=paths.root, shell=True, text=True, capture_output=True, check=False)
            output = (process.stdout or "") + (process.stderr or "")
            log_path = log_dir / f"{index:02d}.log"
            log_path.write_text(output, encoding="utf-8")
            receipts.append(
                {
                    "command": command,
                    "exit_code": process.returncode,
                    "summary": compact(output, max_lines),
                    "full_log": paths.relative(log_path),
                }
            )
            if process.returncode != 0:
                final_code = process.returncode
                break
        result = {
            "status": "passed" if final_code == 0 else "failed",
            "profile": profile,
            "commands": receipts,
        }

    receipt_path = receipt_dir / f"{stamp}-{profile}.json"
    receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["receipt"] = paths.relative(receipt_path)
    print_json(result)
    return final_code
