# Group Consolidation for Odoo 20

An Odoo 20 Community module that produces group results for a multi-company,
multi-currency group, with intercompany eliminations an auditor can open.

> Work in progress. Sections marked TODO are filled in as the module is built.

## Requirements

- Docker with the Compose plugin
- GNU Make
- Optional, for `make lint`: [ruff](https://docs.astral.sh/ruff/)

## Quick start

```bash
git clone <this repository>
cd <repository>
make demo     # creates database "delta" with the module and demo data, starts Odoo
```

Open http://localhost:8020 and log in as `admin` / `admin`.

| Command | What it does |
|---|---|
| `make demo` | Recreate the demo database from scratch (one command) |
| `make test` | Run the automated tests on a throw-away database |
| `make up` / `make down` | Start / stop the containers |
| `make help` | List every target |

Port 8020 can be changed with `ODOO_PORT=9000 make demo`.

## Standard Odoo mechanisms used and what was added

TODO

## Checking the group results — five steps for a controller

TODO

## Documents

- `docs/DECISION.md` — how, when and where eliminations are created (TODO)
- `docs/ASSUMPTIONS.md` — assumptions, one line each (TODO)
- `docs/expected_numbers.md` — hand-computed expected figures (TODO)
- `docs/AI_WORKFLOW.md` — how the AI harness works and how its output was verified
