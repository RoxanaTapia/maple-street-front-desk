# Setup guide

How to run the assistant for your business.
The details for this project are in [docs/agreements.md](agreements.md).

## What you need

- A computer with Python 3, at the version named in [.python-version](../.python-version).
- Nothing to install. The programs use only Python's own library.
- A Claude key from your own Anthropic account, with a spend limit set there.

## Try it on your computer

1. Open a terminal in the project folder.
2. Start the chat:

   ```
   python3 scripts/demo_chat.py
   ```

3. Open http://127.0.0.1:8080.

You should see `Demo chat at http://127.0.0.1:8080`, then a page that says it is a demo.
Type a message and a reply comes back. Stop the chat with Ctrl+C.

The chat starts your pages for you, so there is no second program to run.
If that port is already in use, stop the other copy, or set `DEMO_PORT` to another port.

## Your Claude key

The Claude key is set on the machine that runs the assistant. It isn't written into the repo or shown in replies.

```
export ANTHROPIC_API_KEY='...'
```

- Never put the key in the repo or in a chat.
- `CLAUDE_MODEL` is optional, and the default is set in the code.
- Without a key, a stand-in answers, which isn't AI.

## Change what it says

| To change | Edit | Then |
|---|---|---|
| Your pages | Visitor text in `sample-site/`, and the page names in the first sentence under Your pages | Ask again |
| Urgent words | Bold phrases under Urgent messages, and the `>` lines in that section for the reply | Ask again |
| The callback sentence | The `>` lines under When the pages don't say | Ask again |
| Your test questions | Numbered lines under The 15 test questions, with the question ending at `?` | Run the checks |

Each page name needs the same link text in `sample-site/index.html`.
A line that is only bold is a group name, and `from` plus a page name picks the page.

The stand-in reads your test questions. Claude reads your pages and the callback sentence, not that list.

## Check it still works

```
python3 scripts/run_checks.py
```

- OK means every check passed.
- A failure ends with FAILED and names the check that did not match.
- Fix your pages, the agreements, or the assistant, then run the command again.

## Handing over the code

The code is handed over once the work is approved and paid.

- Transfer the repo: Settings, then Danger Zone, then Transfer ownership.
- Or invite a collaborator: Settings, then Collaborators, then Add people.

After a transfer, the repo and the key are yours.
