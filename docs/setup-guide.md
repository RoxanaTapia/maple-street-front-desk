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
| The off-topic reply | The `>` lines under Off-topic questions | Ask again |
| The outage sentence | The `>` lines under When the assistant can't look it up | Ask again |
| Your test questions | Numbered lines under The 16 test questions, with the question ending at `?` | Run the checks |

Each page name needs the same link text in `sample-site/index.html`.
A line that is only bold is a group name, and `from` plus a page name picks the page.

The stand-in reads your test questions. Claude reads your pages and the callback sentence, not that list. A clearly unrelated question uses the off-topic reply and is not sent to Claude. A question we do not recognize still uses the callback sentence. The outage sentence is used when a call fails, and when the demo cannot safely show a reply.

## Check it still works

```
python3 scripts/run_checks.py
```

- OK means every check passed.
- A failure ends with FAILED and names the check that did not match.
- Fix your pages, the agreements, or the assistant, then run the command again.

## Questions

**Where are the rules kept?**
The code reads `docs/agreements.md` on every message: the urgent words and fixed urgent reply, the callback sentence, the off-topic reply, the outage sentence, and the test questions.
You can edit it as plain text. Keep the headings, and run the checks after any change. Other files in docs/ are for reading only.

**Can it make up a price?**
No. Plain code, not AI (`scripts/price_reply.py`), checks every amount in an answer against your pages. The amount has to be written there, exactly as written, on the same page and near the service the customer asked about.
If it isn't, the whole answer becomes the callback.

**What does it cost to run?**
Each question that is not clearly unrelated sends your pages to Claude. With the default small model that's a fraction of a cent per question, roughly a few cents a month for a few hundred questions.
Urgent messages use no AI. A clearly unrelated question is not sent to Claude. See your exact costs on your Anthropic usage page. Hosting is separate.

**What if Claude is down or the key expires?**
The customer gets the outage reply, from When the assistant can't look it up, so they're never left without an answer. A fact the pages don't cover still uses the callback sentence, from When the pages don't say.
Each failure adds a line to `logs/claude-failures.log` on the computer that runs the assistant: the time and the kind of error, with no customer message and no key.
A warning with the kind of error is also printed where the assistant is running.

**What if a page can't be opened?**
The customer gets the same reply as before. A question that needed that page gets the callback sentence. A question another page answers, such as Hours & FAQ, is still answered.
The same file, `logs/claude-failures.log`, gets one line: the time, the page name, and the kind of error. The customer's message is not written there. The same page is noted once an hour.

## Handing over the code

The code is handed over once the work is approved and paid.

- Transfer the repo: Settings, then Danger Zone, then Transfer ownership.
- Or invite a collaborator: Settings, then Collaborators, then Add people.

After a transfer, the repo and the key are yours.

## Versions it was tested on

The assistant was checked with these versions.

- The Claude model is `claude-haiku-5-5`, and you can change it with the `CLAUDE_MODEL` setting.
- Anthropic API version `2023-06-01` is sent with each call.
- Python 3.12 is the version the checks use.
