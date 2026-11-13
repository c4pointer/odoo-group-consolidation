"""PostToolUse hook: run ruff on every Python file the agent has just written.

Exit code 2 sends the findings back to the agent, so lint errors are fixed in
the same step instead of piling up until review.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    event = json.load(sys.stdin)
    path = event.get("tool_input", {}).get("file_path", "")
    if not path.endswith(".py") or not Path(path).is_file():
        return 0
    root = Path(event.get("cwd") or ".").resolve()
    if not Path(path).resolve().is_relative_to(root):
        return 0  # scratch files outside the repository are not linted
    if shutil.which("ruff") is None:
        print("lint hook: ruff is not installed, skipping", file=sys.stderr)
        return 0

    problems = []
    for args in (["check", path], ["format", "--check", "--diff", path]):
        result = subprocess.run(["ruff", *args], capture_output=True, text=True)
        if result.returncode != 0:
            problems.append(result.stdout + result.stderr)

    if problems:
        print(f"ruff found problems in {path}:\n" + "\n".join(problems), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
