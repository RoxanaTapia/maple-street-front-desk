# Setup guide reference

Notes for an engineer. The office steps are in the [setup guide](setup-guide.md).

## If the port is in use

Stop the other copy, or set `DEMO_PORT` to another port.

## The key, the model, and the stand-in

- `CLAUDE_MODEL` is optional. The default is set in the code.
- The tested model, API version, and Python version are in the setup guide, under [Versions it was tested on](setup-guide.md#versions-it-was-tested-on).
- Without a key, a stand-in answers. That stand-in is not the AI.
- The stand-in reads the test questions.
- Claude reads the pages and the callback sentence, not that list.
- A clearly unrelated question uses the off-topic reply and is not sent to Claude.
- A request to ignore the rules, or for a discount, uses the discount reply and is not sent to Claude.
- A service the pages don't list uses that reply and is not sent to Claude.
- A question that asks for an email the pages don't list says so, then uses the callback sentence, and is not sent to Claude.
- A question in two parts answers the part the pages cover and says the other part is not listed.
- A reply that uses facts from more than one page names every page it used.
- An internal note is left out of the reply.
- A question we do not recognize still uses the callback sentence.
- The outage sentence is used when a call fails, and when the demo cannot safely show a reply.

## Change other replies

The office guide covers hours, FAQ, prices, and contact info. These other edits live on the agreements page. Keep the headings. Ask again after a page edit. Run the automated tests after an agreements edit.

| To change | Edit |
|---|---|
| Your pages | Visitor text in `sample-site/`, and the page names in the first sentence under [Your pages](agreements.md#your-pages) |
| Urgent words | Bold phrases under [Urgent messages](agreements.md#urgent-messages), and the `>` lines in that section for the reply |
| The callback sentence | The `>` lines under [When the pages don't say](agreements.md#when-the-pages-dont-say) |
| The off-topic reply | The `>` lines under [Off-topic questions](agreements.md#off-topic-questions) |
| The outage sentence | The `>` lines under [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up) |
| The discount reply | The `>` lines under [Discounts](agreements.md#discounts) |
| A service the pages don't list | The `>` lines under [A service the pages don't list](agreements.md#a-service-the-pages-dont-list) |
| The contact lines in the replies | The steps are in the [handover notes](handover.md#set-your-call-us-number-and-your-emergency-number) |
| The test questions | Numbered lines under [The 18 test questions](agreements.md#the-18-test-questions). The question ends at `?`. A line with no `?` is the whole question. When that line has a second sentence, the first sentence is the question and the second sentence is the detail |

Each page name needs the same link text in `sample-site/index.html`.
A line that is only bold is a group name, and `from` plus a page name picks the page.

## Where the rules are kept

The code reads `docs/agreements.md` on every message.

It reads the urgent words and the fixed urgent reply, the callback sentence, the off-topic reply, the outage sentence, and the test questions.

Edit that file as plain text. Keep the headings. Run the automated tests after any change.

Other files in `docs/` are for reading only.

## Prices

Plain code, not AI, in `scripts/price_reply.py`, compares every amount in an answer with the pages.

The amount has to be written there, exactly as written, on the same page and near the service the customer asked about.

If it is not, the whole answer becomes the callback sentence.

## What it costs

Each question that is not clearly unrelated sends the pages to Claude.

With the default small model that is a fraction of a cent per question, roughly a few cents a month for a few hundred questions.

Urgent messages use no AI.

A clearly unrelated question is not sent to Claude.

See the exact cost on the Anthropic usage page. Hosting is separate.

## When a call or a page fails

The customer gets the outage reply, from When the assistant can't look it up, so they still get an answer.

A fact the pages don't cover still uses the callback sentence, from When the pages don't say.

Each failure adds a line to `logs/error-notes.log` on the computer that runs the assistant.

The line has the time and the kind of error, with no customer message and no key.

A warning with the kind of error is also printed where the assistant is running.

If a page cannot be opened, the customer gets the same kind of reply as before.

A question that needed that page gets the callback sentence.

A question another page answers, such as Hours & FAQ, is still answered.

The same file gets one line: the time, the page name, and the kind of error.

The customer's message is not written there.

The same page is noted once an hour.

## Hand over the repo

The code is handed over once the work is approved and paid.

- Transfer the repo: Settings, then Danger Zone, then Transfer ownership.
- Or invite a collaborator: Settings, then Collaborators, then Add people.

After a transfer, the repo and the key are yours.
