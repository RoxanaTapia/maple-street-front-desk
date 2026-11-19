# Developer guide

> 🛠️ Developer guide: for whoever installs or maintains the front desk.
>
> The office does not need this page.
>
> Their guide is the [setup guide](setup-guide.md).

## 🧰 First install

Nothing else to install.

The programs use only Python's own library.

Put the key on the computer that runs the assistant.

It is not saved in the project.

It is not shown in replies.

```
export ANTHROPIC_API_KEY='...'
python3 scripts/demo_chat.py
```

Open http://127.0.0.1:8080.

You should see `Demo chat at http://127.0.0.1:8080`.

Then a page that says it is a demo.

Stop with Ctrl+C.

The chat starts the pages.

There is no second program.

If that port is already in use, stop the other copy.

Or set `DEMO_PORT` to another port.

## 🔍 See that it still works

```
python3 scripts/run_checks.py
```

OK means every automated test passed.

A failure ends with FAILED.

It names the automated test.

Fix the page or the agreements.

Then run the automated tests again.

## 🔑 Key, model, and stand-in

`CLAUDE_MODEL` is optional.

The default is set in the code.

Tested versions are under [Versions it was tested on](#versions-it-was-tested-on).

That note names the model, the API version, and Python.

Without a key, a stand-in answers.

That stand-in is not the AI.

The stand-in reads the test questions.

Claude reads the pages and the callback sentence.

Claude does not read that list.

- A clearly unrelated question uses the off-topic reply.
- It is not sent to Claude.
- A request to ignore the rules uses the discount reply.
- A request for a discount uses the discount reply.
- Neither request is sent to Claude.
- A service the pages don't list uses that reply.
- It is not sent to Claude.
- An email the pages don't list is named as missing.
- Then the callback sentence is used.
- That question is not sent to Claude.
- A two-part question answers the part the pages cover.
- It says the other part is not listed.
- Facts from more than one page name every page used.
- An internal note is left out of the reply.
- A question we do not recognize uses the callback sentence.
- A failed call uses the outage sentence.
- So does a demo that cannot safely show a reply.

## ✏️ Changing replies, rules, and prices

The office guide covers hours, FAQ, prices, and contact.

Hours and FAQ: visitor text in `sample-site/hours.html`.

Prices: visitor text in `sample-site/pricing.html`.

Contact info: visitor text in `sample-site/contact.html`.

A bigger change is quoted as a new milestone.

Other edits live on the agreements page.

Keep the headings.

Ask again after a page edit.

Run the automated tests after an agreements edit.

- Pages: visitor text in `sample-site/`.
- Page names: first sentence under [Your pages](agreements.md#your-pages).
- Urgent words: bold phrases under [Urgent messages](agreements.md#urgent-messages).
- The urgent reply: the `>` lines in that section.
- Callback sentence: `>` lines under [When the pages don't say](agreements.md#when-the-pages-dont-say).
- Off-topic reply: `>` lines under [Off-topic questions](agreements.md#off-topic-questions).
- Outage sentence: `>` lines under [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up).
- Discount reply: `>` lines under [Discounts](agreements.md#discounts).
- Unlisted service: `>` lines under [A service the pages don't list](agreements.md#a-service-the-pages-dont-list).
- Contact lines in replies: steps in the [handover notes](handover.md#set-your-call-us-number-and-your-emergency-number).
- Test questions: numbered lines under [The 18 test questions](agreements.md#the-18-test-questions).
- The question ends at `?`.
- A line with no `?` is the whole question.
- On that line, the first sentence is the question.
- A second sentence on that line is the detail.

Each page name needs the same link text in `sample-site/index.html`.

A line that is only bold is a group name.

`from` plus a page name picks the page.

The code reads `docs/agreements.md` on every message.

It reads the urgent words and the fixed urgent reply.

It reads the callback sentence.

It reads the off-topic reply.

It reads the outage sentence.

It reads the test questions.

Edit that file as plain text.

Keep the headings.

Run the automated tests after any change.

Other files in `docs/` are for reading only.

`scripts/price_reply.py` is plain code, not AI.

It compares every amount in an answer with the pages.

The amount must be written there, exactly as written.

It must be on the same page.

It must be near the service the customer asked about.

If it is not, the whole answer becomes the callback sentence.

## 💸 What it costs

Each question that is not clearly unrelated sends the pages to Claude.

The default small model is a fraction of a cent per question.

A few hundred questions are roughly a few cents a month.

Urgent messages use no AI.

A clearly unrelated question is not sent to Claude.

See the exact cost on the Anthropic usage page.

Hosting is separate.

## 🚑 When something fails

The customer gets the outage reply.

It comes from When the assistant can't look it up.

They still get an answer.

A fact the pages don't cover uses the callback sentence.

That sentence comes from When the pages don't say.

Each failure adds a line to `logs/error-notes.log`.

That file is on the computer that runs the assistant.

The line has the time and the kind of error.

It has no customer message and no key.

A warning is printed where the assistant runs.

The warning names the kind of error.

If a page cannot be opened:

The customer gets the same kind of reply as before.

A question that needed that page gets the callback sentence.

A question another page answers is still answered.

Hours & FAQ is one example.

The same file gets one line.

That line has the time, the page name, and the error kind.

The customer's message is not written there.

The same page is noted once an hour.

## 📦 Handing over

The code is handed over once the work is approved and paid.

Transfer the repo: Settings, then Danger Zone, then Transfer ownership.

Or invite a collaborator: Settings, then Collaborators, then Add people.

After a transfer, the repo and the key are yours.

## Versions it was tested on

- The Claude model is `claude-haiku-5-5`.
- Change it with `CLAUDE_MODEL`.
- The API version is `2023-06-01`.
- Python 3.12 is for the automated tests.
