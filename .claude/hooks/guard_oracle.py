"""PreToolUse hook: the agent may not change the hand-computed expected figures.

The expected figures are the test oracle. They are computed by hand from the
scenario, independently of the code. If the agent could edit them, a failing
test could be "fixed" by moving the goalposts. A human edits these files in
the editor and commits them; the agent only reads them.

Protected paths (relative to the repository root):
  docs/expected_numbers.md
  addons/*/tests/expected_*.py

This is a guardrail, not a sandbox: it stops the obvious paths (Edit/Write and
shell commands that name the file). Every change to these files is still
visible in `git log` and must be reviewed by a human.
"""

import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

PROTECTED_GLOBS = (
    "docs/expected_numbers.md",
    "addons/*/tests/expected_*.py",
)
# Shell fragments that read but never write.
READ_ONLY_COMMANDS = re.compile(
    r"^\s*(cat|less|head|tail|grep|rg|wc|diff|git (diff|log|show|blame|status))\b"
)
REASON = (
    "Blocked by .claude/hooks/guard_oracle.py: this file holds the hand-computed "
    "expected figures (the test oracle). The agent must not change it. If the "
    "numbers look wrong, explain why and let the human edit the file."
)


def is_protected(path: str, root: Path) -> bool:
    try:
        rel = Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return False
    return any(fnmatch(rel, pattern) for pattern in PROTECTED_GLOBS)


def shell_touches_oracle(command: str) -> bool:
    mentions = "expected_numbers" in command or re.search(r"tests/expected_\w*\.py", command)
    return bool(mentions) and not READ_ONLY_COMMANDS.match(command)


def main() -> int:
    event = json.load(sys.stdin)
    root = Path(event.get("cwd") or ".")
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    if tool == "Bash":
        blocked = shell_touches_oracle(tool_input.get("command", ""))
    else:
        blocked = is_protected(
            tool_input.get("file_path") or tool_input.get("notebook_path") or "", root
        )

    if blocked:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": REASON,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
