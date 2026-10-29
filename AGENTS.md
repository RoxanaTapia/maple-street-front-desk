# Maple Street Front Desk

Project guide. [README.md](README.md) says what this project is. This page is the layout, how to run the checks, how a change is made, and what stays fixed unless the client agrees.

## Folder map

| Path | What it is |
|---|---|
| [README.md](README.md) | What the project is |
| [AGENTS.md](AGENTS.md) | This guide |
| [.python-version](.python-version) | Pinned Python version |
| [scripts/run_checks.py](scripts/run_checks.py) | Runs the checks |
| [tests/](tests/) | Automatic checks |
| [.cursor/rules/answers.mdc](.cursor/rules/answers.mdc) | How questions are answered |
| [.cursor/rules/urgent-and-price.mdc](.cursor/rules/urgent-and-price.mdc) | Urgent replies and prices |
| [.cursor/rules/tests.mdc](.cursor/rules/tests.mdc) | How the checks stay strict |
| [.cursor/team/README.md](.cursor/team/README.md) | Roles |
| [.cursor/commands/run-checks.md](.cursor/commands/run-checks.md) | Shortcut: run the checks |
| [.cursor/commands/pr-summary.md](.cursor/commands/pr-summary.md) | Shortcut: write the change summary |
| [.github/pull_request_template.md](.github/pull_request_template.md) | Summary that comes with every change |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | Runs the checks on every pull request |

Planned. These are not in the repo yet.

| Path | What it is |
|---|---|
| `sample-site/` | A small fictional sample of the business's public pages |
| `src/` | Reads those pages and answers questions |
| `tests/expected-answers.md` | The agreed questions and the answers we expect |
| `tests/urgent-words.md` | The agreed urgent words |
| `requirements.txt` | Project dependency file |
| `docs/setup.md` | How to run the project |
| `docs/handover.md` | Notes for handover |

## How to run the checks

Follow [.cursor/commands/run-checks.md](.cursor/commands/run-checks.md).

## How a change is made

1. One issue.
2. One branch.
3. One pull request. Use the summary template, and write it with [.cursor/commands/pr-summary.md](.cursor/commands/pr-summary.md).
4. Automatic checks.
5. A person reviews the change.
6. Merge.

Roles for that work are in [.cursor/team/README.md](.cursor/team/README.md).

## What never changes without the client's OK

- **Urgent reply text**

  > This sounds urgent. Please call us now on (856) 555-0142.

- **Expected test answers.** The expected-answers file in the folder map, once it has been agreed.
- **Pinned engine version.** The answer engine is pinned to one tested version in `requirements.txt`, once that file is added.

Behaviour rules are in [.cursor/rules/](.cursor/rules/).
