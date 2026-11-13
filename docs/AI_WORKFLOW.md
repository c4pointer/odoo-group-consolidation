# How this was built with AI

The agent is Claude Code. This page describes the harness around it: what the
agent may do, what it may not do, and how its output is verified.

## The harness

| Part | File | Purpose |
|---|---|---|
| Project instructions | `CLAUDE.md` | Scope, hard rules, commands and domain glossary loaded into every session |
| Oracle guard | `.claude/hooks/guard_oracle.py` | Blocks the agent from editing the hand-computed expected figures |
| Lint on write | `.claude/hooks/lint_python.py` | Runs ruff after every Python edit and returns findings to the agent |
| Hook tests | `.claude/hooks/test_hooks.py` | `make harness` proves the guard blocks writes and allows reads |
| Permissions | `.claude/settings.json` | Allows the routine commands; denies amend, rebase and force push |
| One-command checks | `Makefile` | `make test` runs the module tests on a fresh database and fails loudly |

## How the output is verified

1. **Independent oracle.** The expected figures in `docs/expected_numbers.md`
   are computed by hand from the scenario before the code exists. Tests compare
   the module's numbers with them. The agent cannot edit that file.
2. **Red before green.** Tests are committed before the logic that makes them
   pass, so the history shows each edge case failing first.
3. **Review.** Each step gets an independent review by a fresh agent with no
   access to the author's reasoning, then a human review of the diff.
4. **Running system.** Numbers are also checked in the running database, both
   through the UI and by querying it.

## Who did what

Filled in as the work progresses; commits made with the agent carry a
`Co-Authored-By` trailer.
