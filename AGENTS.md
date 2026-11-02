# Project guide

This is the project guide. I build your assistant with AI coding agents, and every agent reads this file first, like a briefing for a new team member. It tells them what we're building, what you've agreed, and how a change is allowed to happen. You can read it too: it's the shortest way to see how your project is run.

## What we're building

Maple Street Front Desk is a chat assistant for your customers. It answers from your own public web pages, and [How your assistant behaves](docs/behaviour.md) is the full description of what it does.

## What we've agreed

These never change without your OK. The list is in [What we've agreed](docs/agreements.md).

## How a change happens

1. **One issue.** An issue is the written request. Each request stays one piece of work.
2. **One branch.** A branch is a separate copy of the project, so this work does not mix with anything else. Its name is plain and descriptive, such as step-5-price-rule.
3. **One pull request.** A pull request is the proposal to add that copy. The title is a plain sentence, with no prefix such as "fix:". Issue titles and pull request titles never use an emoji. Emojis are only for the section headings. The description follows [the change summary](.github/pull_request_template.md): it starts with Closes #N, then one or two optional plain sentences saying why this step comes at this point in the plan. Next is 📝 What changes as short bullets. Then ⚙️ How it works: two or three plain sentences on why the change exists and what it does, starting from the risk it handles (for example, "The AI can make up a price, so we check what it's about to say."), then a "Not covered yet" list of at most a few one-line bullets naming which step covers each. No implementation detail, and no code terms. Then ✅ Checks, with a link to that pull request's checks tab. When the checks have passed, the link reads All checks passed, and any new check is named there. List the acceptance boxes from the issue that this change covers. Leave out How it was tested, leave out Try it, and don't link to test files.
4. **Automatic checks.** So nothing breaks what you agreed. Each new test area gets its own plainly named check on the pull request.
5. **A person reviews.** A person signs off every change.
6. **Merge.** Merge means the change joins the project.

## Where things are

| Group | File | What it is |
|---|---|---|
| For you | [README.md](README.md) | What this project is |
| For you | [docs/agreements.md](docs/agreements.md) | What we've agreed |
| For you | [docs/behaviour.md](docs/behaviour.md) | What the assistant does for a customer |
| For you | [AGENTS.md](AGENTS.md) | This guide |
| For you | [sample-site/](sample-site/) | A small fictional sample of your public pages |
| For you | [scripts/serve_sample_site.py](scripts/serve_sample_site.py) | Serves that sample like a website |
| For you | [scripts/read_pages.py](scripts/read_pages.py) | Reads the agreed pages and prints the page list. See [How your pages are read](docs/behaviour.md#how-your-pages-are-read). |
| For you | [scripts/urgent_reply.py](scripts/urgent_reply.py) | Checks a customer message for your urgent words and prints the fixed reply. See [How it works](docs/behaviour.md#how-it-works). |
| For the agents | [docs/contributing.md](docs/contributing.md) | How to run the sample site and the checks. See [How to run it](docs/contributing.md#how-to-run-it). |
| For the agents | [.cursor/rules/](.cursor/rules/) | How the agents are allowed to work |
| For the agents | [.cursor/team/](.cursor/team/README.md) | The roles they work in |
| For the agents | [.cursor/commands/](.cursor/commands/run-checks.md) | Shortcuts for the checks and the change summary |
| Checks | [tests/](tests/) | The automatic checks |
| Checks | [scripts/run_checks.py](scripts/run_checks.py) | Runs the checks |
| Checks | [.github/workflows/ci.yml](.github/workflows/ci.yml) | Runs those same checks on every proposed change |
| Checks | [.github/pull_request_template.md](.github/pull_request_template.md) | The short form for the change summary |
| Checks | [.python-version](.python-version) | Which version of Python the checks use. Python is the language they are written in. |
| Coming in a later step | `src/` | The assistant itself, which reads pages and answers |
| Coming in a later step | `requirements.txt` | The list of parts the project needs |
| Coming in a later step | `docs/setup.md` | How to run the project |
| Coming in a later step | `docs/handover.md` | Notes for when the project is handed to you |

To try the sample site, read the pages, or run the checks, follow [How to run it](docs/contributing.md#how-to-run-it).

## For the agents

Three layers. [What we've agreed](docs/agreements.md) wins if anything else disagrees. [How your assistant behaves](docs/behaviour.md) says what the assistant does. The code (the part that does the work) and the checks prove it.

`.cursor/` is the instructions for the agents that build it. How you work: [.cursor/rules/](.cursor/rules/). Roles: [.cursor/team/README.md](.cursor/team/README.md).
