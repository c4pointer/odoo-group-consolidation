"""Tests for the Claude Code hooks. Run with: python3 -m unittest discover -s .claude/hooks"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
ROOT = HOOKS.parent.parent
ORACLE_DOC = ROOT / "docs" / "expected_numbers.md"
ORACLE_PY = ROOT / "addons" / "account_group_consolidation" / "tests" / "expected_figures.py"


def run_guard(tool_name: str, tool_input: dict) -> str:
    event = {"cwd": str(ROOT), "tool_name": tool_name, "tool_input": tool_input}
    result = subprocess.run(
        [sys.executable, "-I", str(HOOKS / "guard_oracle.py")],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=True,
    )
    return "deny" if '"deny"' in result.stdout else "allow"


class TestGuardOracle(unittest.TestCase):
    def test_edit_and_write_on_oracle_are_denied(self):
        self.assertEqual(run_guard("Edit", {"file_path": str(ORACLE_DOC)}), "deny")
        self.assertEqual(run_guard("Write", {"file_path": str(ORACLE_PY)}), "deny")

    def test_other_files_are_allowed(self):
        test_file = ORACLE_PY.with_name("test_eliminations.py")
        self.assertEqual(run_guard("Edit", {"file_path": str(test_file)}), "allow")
        self.assertEqual(run_guard("Write", {"file_path": str(ROOT / "README.md")}), "allow")

    def test_shell_writes_to_oracle_are_denied(self):
        doc = ORACLE_DOC.relative_to(ROOT).as_posix()
        py = ORACLE_PY.relative_to(ROOT).as_posix()
        for command in (f"sed -i s/1/2/ {doc}", f"echo x > {py}", f"cp /tmp/x {doc}"):
            with self.subTest(command=command):
                self.assertEqual(run_guard("Bash", {"command": command}), "deny")

    def test_shell_reads_of_oracle_are_allowed(self):
        doc = ORACLE_DOC.relative_to(ROOT).as_posix()
        for command in (f"cat {doc}", f"git diff {doc}", f"grep USD {doc}"):
            with self.subTest(command=command):
                self.assertEqual(run_guard("Bash", {"command": command}), "allow")


if __name__ == "__main__":
    unittest.main()
