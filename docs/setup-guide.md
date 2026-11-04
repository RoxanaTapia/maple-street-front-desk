# Setup guide

This is how to run Maple Street Front Desk, for Dave and for whoever runs it for him.

The assistant answers from the business's pages. An urgent message gets a reply that tells the customer to call now. A price is kept only when those pages state it. For now it reads a practice copy of the site. The assistant only reads the pages and never changes the owner's website, which the owner keeps editing.

## What's in this project

| Place | What it is |
|---|---|
| [README.md](../README.md) | What this project is |
| [docs/agreements.md](agreements.md) | The pages, the urgent words, the callback sentence, and the 15 test questions |
| [docs/behaviour.md](behaviour.md) | What a customer gets back |
| [docs/how-it-works.md](how-it-works.md) | The path of a message, and the commands to try |
| [docs/setup-guide.md](setup-guide.md) | This guide |
| [docs/test-results.md](test-results.md) | The live demo on Nov 4, 2026 |
| [sample-site/](../sample-site/) | The practice copy of the six pages |
| [demo/](../demo/) | The chat page |
| [scripts/](../scripts/) | The programs that read the pages, answer, and run the checks |
| [tests/](../tests/) | The automatic checks |

[AGENTS.md](../AGENTS.md) is the guide for the people building this. You do not need it to run the assistant.

## What it needs

Python 3.12. That version is named in [.python-version](../.python-version), and the checks use it.

The programs in `scripts/` use only Python's standard library. There is nothing to install, and there is no list of extra parts.

## Try it on your computer

From the project folder:

```
python3 scripts/demo_chat.py
```

It prints `Demo chat at http://127.0.0.1:8080`. Open that address. The page says this is a demo and that it answers only from Maple Street's pages. Type a message and the reply comes back. Stop it with Ctrl+C.

The chat starts the practice site itself, so you do not start that site first. If the port is already in use, the script says to stop the other copy, or to set `DEMO_PORT` to another port.

`DEMO_HOST` and `DEMO_PORT` choose where the chat listens. Leave them empty and the address is `http://127.0.0.1:8080`. The names are listed in [.env.example](../.env.example).

Start the practice site yourself when a command reads `http://127.0.0.1:8000`. Those commands are in [Try it yourself](how-it-works.md#try-it-yourself). From the project folder:

```
python3 scripts/serve_sample_site.py
```

It prints `Serving the sample site at http://127.0.0.1:8000`. Leave it running, and use a second terminal for the other command. Stop it with Ctrl+C. If the port is already in use, the script says to stop the other copy, or to start on another port with `--port`.

## The Claude key

The Claude key is set on the machine that runs the assistant. It isn't written into the repo or shown in replies.

Set `ANTHROPIC_API_KEY` in the environment on that machine. Do not paste the key into the chat, and do not save it in a file in this project.

The key comes from your own Anthropic account. Set the spend limit on that account. This project has no setting for a spend limit.

```
export ANTHROPIC_API_KEY='...'
```

The dots stand in for the key. They are not a key.

`CLAUDE_MODEL` is optional. The default is set in the code. Both names are listed in [.env.example](../.env.example), with empty values. The programs read the environment. They do not read that file.

With no key, a stand-in answers. The stand-in is not a real AI. It answers the test questions in the group "Answered by your pages" when the named page's text supports the note, and it answers "What are your hours?" from the Hours & FAQ page. The answer ends with From and the page name. Anything else the stand-in is asked gets the callback sentence.

If the call to Claude fails, the customer gets the callback sentence.

## When a page changes

Today the assistant reads the practice copy in `sample-site/`.

| Page | File |
|---|---|
| Home | `sample-site/index.html` |
| Services | `sample-site/services.html` |
| Pricing | `sample-site/pricing.html` |
| Service Area | `sample-site/service-area.html` |
| Hours & FAQ | `sample-site/hours.html` |
| Contact | `sample-site/contact.html` |

To change what a page says, edit the words a visitor sees in that file, then start the chat again.

The page names come from the first sentence under [Your pages](agreements.md#your-pages). The path for each name comes from the navigation links in `sample-site/index.html`. The link text has to match the page name. A link of `index.html` or `/` is the home page. Any other link is the path, with a `/` added in front when the link has none.

The chat serves that practice copy. It does not take a site address.

The command-line programs can read another site. Put the address last. It has to start with `http://` or `https://`.

```
python3 scripts/read_pages.py http://127.0.0.1:8000
python3 scripts/front_desk.py 'Are you open Saturdays?' http://127.0.0.1:8000
```

`scripts/answer_reply.py` and `scripts/price_reply.py` take an address the same way. The paths are still the ones from the practice navigation, added to that address. Another site works when those paths exist there. There is no separate setting for a site address.

## Change a reply or a test question

Urgent words, the callback sentence, and the 15 test questions are in [What we've agreed](agreements.md). The programs read that file.

**Urgent words.** Under [Urgent messages](agreements.md#urgent-messages), each phrase in bold is an urgent word. Capitals do not matter. The phrase has to stand on its own, so "frozen pipes" is not the word "frozen pipe".

**The urgent reply.** Under the same heading, the lines that start with `>` are joined into the reply. That reply tells the customer to call now. An urgent message stops there, and the pages are not read.

**The callback sentence.** Under [When the pages don't say](agreements.md#when-the-pages-dont-say), the lines that start with `>` are joined into the callback sentence. The assistant uses it when the pages do not cover the question, and when a price is not written on the pages.

**The 15 test questions.** Under [The 15 test questions](agreements.md#the-15-test-questions), a line that is only bold text is a group name. A numbered line is one question. The question is the text up to the question mark. The note after it is the detail. When the detail says "from" and a page name, that names the page. The stand-in uses this list. With `ANTHROPIC_API_KEY` set, Claude does not read the list. Claude reads the page text and the callback sentence. The checks read the list too.

The checks still expect the list to stay as it is written: 15 questions, numbered 1 to 15, the group names "Answered by your pages" and "Handled by a set reply", and the first six questions in their current words. They also expect the callback sentence to stay "I can't confirm that from your pages.", the urgent word "frozen pipe" to stay, and the phone number (856) 555-0142 to stay in that file. Changing those makes a check fail. Run the checks after an edit.

## Run the checks

From the project folder:

```
python3 scripts/run_checks.py
```

Each check prints ok, and the run ends with OK. The assistant still matches what was agreed.

If a check fails, the run ends with FAILED and prints the check that did not match. Something in the pages, the agreements, or the assistant no longer lines up with what was agreed. Fix that, then run the command again.

## The version

The live demo at <https://maple-demo.roxanatapia.dev> ran on Nov 4, 2026, from main at commit `e0a24d614d51d94c1dddc8974039def061cefe3d` (`e0a24d6`). The results are in [Live test results](test-results.md).

This guide is written against main at commit `36b6eafcd8619fb0b450a8d899915b858c63bd6d` (`36b6eaf`). That is the demo commit, plus a wording change in the README and in [How the assistant works](how-it-works.md). The programs are the same. There is no release tag.

On your copy, this prints the commit you have:

```
git log -1
```

## Handing over the code

Development happens in Roxana's GitHub repo, and the code is handed over once the work is approved and paid.

At handover there are two options. Option one: Roxana transfers the repo to the client's GitHub account (in GitHub: Settings, then Danger Zone, then Transfer ownership). The client accepts the transfer and can keep Roxana as a collaborator for later fixes.

Option two: the client is invited as a collaborator (Settings, then Collaborators, then Add people).

After a transfer, the client owns the repo, its history, and the setup, and the Claude key stays in their own account.

The hosted demo link runs during this first version and for 14 days after delivery, as agreed in the issue.
