"""PreToolUse hook: the agent may not change the hand-computed expected figures.

The expected figures are the test oracle. They are computed by hand from the
scenario, independently of the code. If the agent could edit them, a failing
test could be "fixed" by moving the goalposts. A human edits these files in
the editor and commits them; the agent only reads them.

Protected paths (relative to the repository root):
  docs/expected_numbers.md
  addons/*/tests/expected_*.py
  .claude/settings.json and this file, so the agent cannot switch the guard off

This is a guardrail, not a sandbox: it stops the obvious paths (Edit/Write and
shell commands that name the file). A shell command that names a protected
file is allowed only when it is a single read-only command with no redirection,
pipes, chaining, substitution or output flags. Every change to these files is
still visible in `git log` and must be reviewed by a human.
"""

import json
import re
import sys
from fnmatch import fnmatch
from pathlib import Path

PROTECTED_GLOBS = (
    "docs/expected_numbers.md",
    "addons/*/tests/expected_*.py",
    ".claude/settings.json",
    ".claude/hooks/guard_oracle.py",
)
# Text that marks a shell command as touching a protected file.
MENTIONS = re.compile(r"expected_numbers|tests/expected_|guard_oracle|\.claude/settings")
# Commands that read but never write...
READ_ONLY_COMMANDS = re.compile(
    r"^\s*(cat|less|head|tail|grep|rg|wc|diff|git (diff|log|show|blame|status))\s"
)
# ...as long as nothing redirects, chains, substitutes or writes an output file.
SHELL_WRITE_RISK = re.compile(r"[;&|<>`\n]|\$\(|--output|(^|\s)-o(\s|$)")
REASON = (
    "Blocked by .claude/hooks/guard_oracle.py: this file is human-owned (the "
    "hand-computed test oracle or the guard itself). The agent must not change "
    "it. Explain the proposed change and let the human edit the file."
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
