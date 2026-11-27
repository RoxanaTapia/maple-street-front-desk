# Project guide

## What we're building

Maple Street Front Desk is a chat assistant for Maple Street Plumbing, a fictional plumbing business. It is a demo front desk. It answers from the business's own public web pages. [How the assistant behaves](docs/behaviour.md) is what a visitor experiences, and [How the assistant works](docs/how-it-works.md) is how a message gets there.

The pages, the urgent words, and the test questions are in [What we've agreed](docs/agreements.md). They stay as they are unless Roxana reviews and merges a change.

## How a change happens

1. **One issue.** An issue is the written request. Each request stays one piece of work. Use `.github/ISSUE_TEMPLATE.md`. The sections are What, Acceptance criteria, and Out of scope, in plain words. Acceptance criteria are plain bullet points, not checkboxes. The title starts with one emoji code, such as 🛠️ or 📄.
2. **One branch.** A branch is a separate copy of the project, so this work does not mix with anything else. Its name is plain and descriptive, such as step-5-price-rule.
3. **One pull request.** A pull request is the proposal to add that copy. The title is a plain sentence, with no prefix such as "fix:". The description is written in plain words. It has four parts: Closes, What changes, How to try it, and Automated tests. There is no Coming next part. Internal review notes stay out of the description. When a change adds or changes a script, update its section in docs/how-it-works.md (what it does, why it's there, a command to try).
4. **Automated tests.** Every change runs the automated tests. Each new test area gets its own plainly named automated test on the pull request.
5. **Roxana reviews and merges.** Roxana reviews every change and merges it.

Public writing uses plain words, with no em dashes and no square brackets.

## Where things are

| Group | Where | What it is |
|---|---|---|
| Public | [README.md](README.md) | What this project is |
| Public | [docs/behaviour.md](docs/behaviour.md) | What a visitor writes, and what they get back |
| Public | [docs/agreements.md](docs/agreements.md) | The pages, the urgent words, and the test questions |
| Public | [docs/how-it-works.md](docs/how-it-works.md) | How a message is handled, and how to try the sample site and the tests |
| Public | [docs/handover.md](docs/handover.md), [docs/portfolio.md](docs/portfolio.md) | Handover notes, and the booking page address the chat footer uses |
| Public | [docs/setup-guide.md](docs/setup-guide.md), [docs/developer-guide.md](docs/developer-guide.md) | Setup, and the notes for someone changing the code |
| Demo | [sample-site/](sample-site/), [demo/](demo/), [vendor/demo-kit/](vendor/demo-kit/) | The sample pages, the chat page, and the shared header, theme, icons, and fonts |
| Scripts | [scripts/](scripts/), [scripts/answer_kinds/](scripts/answer_kinds/) | The front desk, the page reader, one file for each kind of reply, the demo chat, and the test runner |
| Agents | [.cursor/rules/](.cursor/rules/), [.cursor/team/](.cursor/team/README.md), [.cursor/commands/](.cursor/commands/run-checks.md) | The rules, the roles, and the shortcuts |
| Checks | [tests/](tests/), [scripts/run_checks.py](scripts/run_checks.py), [.github/workflows/ci.yml](.github/workflows/ci.yml) | The automated tests, the runner, and the workflow on every proposed change |
| Checks | [.github/ISSUE_TEMPLATE.md](.github/ISSUE_TEMPLATE.md), [.github/pull_request_template.md](.github/pull_request_template.md) | The short issue form and the short pull request form |
| Style | [pyproject.toml](pyproject.toml), [.editorconfig](.editorconfig), [.python-version](.python-version) | Ruff settings, editor settings, and the Python version |
| Guide | [AGENTS.md](AGENTS.md) | This guide |

## Tests

From the project root, with the Python version in [.python-version](.python-version):

```bash
python3 scripts/run_checks.py
ruff check .
ruff format --check .
```

One area is the same runner with a file, for example `python3 scripts/run_checks.py tests/test_checks.py`. These commands run on every pull request. To try the sample site, follow [Try it yourself](docs/how-it-works.md#try-it-yourself).

## For the agents

Do:

- Read this guide and [docs/behaviour.md](docs/behaviour.md) before you edit.
- Stay inside the current issue, and follow [How a change happens](#how-a-change-happens).
- Match [docs/behaviour.md](docs/behaviour.md) when a change touches how the assistant behaves.
- Run the commands in [Tests](#tests) before a pull request is ready for review.

Don't:

- Change [docs/agreements.md](docs/agreements.md), or weaken a test so it passes. Roxana reviews and merges any change to what was agreed.
- Describe Maple Street Plumbing as a real client. It is a demo front desk.
- Change how the assistant behaves unless the issue asks for that.

[What we've agreed](docs/agreements.md) wins if anything else disagrees. [How the assistant behaves](docs/behaviour.md) says what the assistant does. The code and the automated tests prove it. Roles are in [.cursor/team/README.md](.cursor/team/README.md).
