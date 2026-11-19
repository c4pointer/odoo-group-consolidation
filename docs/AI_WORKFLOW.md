# How this was built with AI

The agent is Claude Code (Claude Opus 5.5). This page describes the harness
around it: what the agent may do, what it may not do, how its output was
verified, and who did what.

## The harness

| Part | File | Purpose |
|---|---|---|
| Project instructions | `CLAUDE.md` | Scope, hard rules, commands and domain glossary loaded into every session |
| Oracle guard | `.claude/hooks/guard_oracle.py` | Blocks the agent from editing, staging or committing the hand-computed expected figures, the settings and the guard itself |
| Lint on write | `.claude/hooks/lint_python.py` | Runs ruff after every Python edit and returns findings to the agent |
| Hook tests | `.claude/hooks/test_hooks.py` | `make harness` proves the guard blocks writes and shell bypasses and allows reads |
| Permissions | `.claude/settings.json` | Allows the routine commands; denies amend, rebase and force push |
| One-command checks | `Makefile` | `make test` runs the module tests on a fresh database and fails loudly |

## How the output was verified

1. **An oracle the agent cannot change.** The expected figures in
   `docs/expected_numbers.md` were worked out from the scenario before the
   module code existed. Tests compare the module's numbers with them. The guard
   stops the agent from editing or even staging these files, so a failing test
   cannot be fixed by moving the expected number.
2. **Red before green, checked by running.** Tests were committed before the
   code that makes them pass. Before each commit the staged tree was exported
   on its own (`git checkout-index`) and tested, so a commit marked red was seen
   failing for the stated reason, and a commit marked green was seen passing.
3. **Tests of the tests.** Every new test was first seen failing against the
   code it guards. Two tests passed on buggy code at first and were rewritten
   until they failed. Three deliberate bugs (balance sheet at the average rate,
   exchange differences taken at zero, no partner-scope filter) were each caught
   by at least one test. The fourth-company test passed on its first run, so it
   was checked the same way: with Delta Germany taken out of the group, 23
   checks in 5 tests fail.
4. **Independent review.** A fresh subagent with the task, the code and the
   oracle, but not the author's reasoning, reviewed the module before its commit
   and reported ten findings. An automated security review ran after the push.
5. **A fresh install.** The repository was cloned from GitHub into an empty
   directory and installed with `make demo` under its own Compose project, then
   the controller steps from the README were run through the API as the `admin`
   user. This was repeated on the final history: both install paths, every
   figure in the five steps and the 56 tests matched, with nothing to fix.
6. **The README in the browser.** The agent clicked through the five
   controller steps as `admin` and recorded them, and the human checked the
   screens against the task. These walks found defects no test could see,
   because the tests read the database, not the screens.
7. **Reading the code for edge cases.** After the oracle tests passed, the
   module was read for situations the scenario does not contain. Each one found
   became a failing test first (`18e884b`, marked red), then a fix.

## What each check caught

| Check | Found |
|---|---|
| Independent review (subagent) | 10 findings: a document posted into a closed month stayed in the group; a full offset within a month at two daily rates left a phantom USD amount; the scheduled action re-ran signed-off months; a contact of a group company was not intercompany; three smaller code issues (rate dates, lock-date exceptions, the report summing across runs) and three places where the docs and the code disagreed. All fixed in `2a31ac6` |
| Red-state check on new tests | Two tests that passed on the buggy code: one masked by a real March invoice, one by Odoo setting the commercial partner on invoice lines |
| Automated security review | The scheduled action runs as superuser; could a manager configure a group over companies they cannot read? Odoo 20 already refuses it; the test in `59b9153` pins that |
| Fresh install from GitHub | `admin` could not see any Delta company, so no README step could be followed (fixed in `5dfa6b9`); a wrong UAH rate and a wrong menu path in the README draft. The tests could not catch these: they run as the superuser. The repeat on the final history found nothing |
| UI walk-through as `admin` | A menu hidden from `admin` and a report that mixed totals (`8d2451c`). The report menu summed every closed month when it could not pick one, found on the human's screenshot (`970520b`); a read-only accountant got an access error from the same menu (`34a3816`) |
| README steps in the browser | Journal items and the Review menu hidden from `admin`, who lacked "Show Full Accounting Features"; elimination entries listed with invoice columns; the report title without its month (`5821c09`) |
| Edge-case reading | An intercompany invoice in a third currency reported a false cash in transit of 666.67 (`dae3687`); a payment moved out of a closed month went unnoticed (`b55bc5d`); the rates of a closed month could still be changed (`c4faca8`). A fourth company needed configuration only, no code (`9ff4eee`) |
| Automated security review, sharing | The public tunnel exposes the demo login: kept, as the human chose it, with the database manager turned off. The proxy showed every visitor to Odoo as one address, so a few wrong passwords locked everyone out (`d3d29db`) |
| Oracle guard | Blocked the agent's own `git add` of the oracle; the human committed it. Later it blocked shell commands that only named the oracle in a search, so the agent read it with the file tool instead |

## Who did what

**The human (Oleg Zubak)**

- Set the scope: Odoo 20 Community only, a public repository, a local Docker
  runtime first.
- Owns the oracle: the drafts were handed over for review, and only the human
  could put them into the repository (`b54baf9`).
- Applied the guard changes the agent prepared as a patch, because the guard
  blocks the agent from editing itself (`4aaad50`).
- Signs every commit with GPG, approves the agent's permissions, and walks
  through the demo in the UI. Screenshots from these walks led to the report
  menu fixes.
- Chose how the demo is shared (a public link with the demo login) and set up
  the Tailscale account that serves the permanent link.

**The agent (Claude Code)**

- Wrote the module, the Delta scenario, the demo module, the tests, the hooks
  and their tests, and drafted every document, including the worked
  calculation behind the oracle.
- Ran lint and tests before each commit, the red-state checks, the mutation
  checks, the fresh installs and the browser walk-throughs.

**Subagents and automated checks**

- A fresh subagent did the independent review, and another one reviewed each
  later change before its commit.
- The security-guidance plugin reviewed the pushed changes.
- ruff ran after every Python edit.

**Commit by commit**

| Commit | By |
|---|---|
| `d348680` to `10a379e` except `4aaad50` | Agent, with a `Co-Authored-By` trailer |
| `4aaad50` | Human, applying the agent's patch to the guard |
| `b54baf9` | Human: the oracle |
| `1324712`, `fadef9d`, `1217f91`, `2a31ac6`, `59b9153`, `5dfa6b9`, `a1641b9` | Agent; the trailer was left out by mistake, and the history is not rewritten to add it |
| `bb977a6` | Committed from the IDE while the agent was rewriting that test; `59b9153` simplified it two minutes later |
| `49d3ca5` | Agent, with a `Co-Authored-By` trailer |
| `8d2451c` to the latest commit | Agent, with a `Claude-Session` trailer linking the session. `8d2451c` is the one unsigned commit; the human allowed it without a signature |

## Known limits

- The worked calculation behind the oracle was drafted by the same model that
  wrote the code. What keeps it independent: it was derived from the scenario
  before any module code existed, it is plain arithmetic a person can check
  line by line, and the agent cannot change it afterwards.
- The guard matches command text, so a path built by shell expansion would pass.
  It stops accidental goalpost-moving, not a hostile agent; every change to the
  oracle is still visible in `git log`.
- Most module tests run as the superuser, so they do not see per-user access.
  The fresh installs and the browser walks cover it for `admin`; tests as a
  restricted user cover group configuration and the report menu for a
  read-only accountant.
- An exchange difference Odoo posts on an intercompany document in a third
  currency is not covered by a test (assumption 35).
