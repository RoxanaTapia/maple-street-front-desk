# Maple Street Front Desk

Maple Street Front Desk is an AI front-desk assistant for a small plumbing business. It answers customer questions only from the business's own pages, tells customers with an urgent problem to call right away, with the business number, and never invents a price.

For now it runs on a small practice copy of the business's site. The assistant only reads the pages and never changes the owner's website, which the owner keeps editing.

## Try it

From the project folder:

```
python3 scripts/demo_chat.py
```

It prints `Demo chat at http://127.0.0.1:8080`. Open that address. The practice site starts with the chat, so there is nothing else to run. Stop it with Ctrl+C. The rest is in the [setup guide](docs/setup-guide.md).

## What customers get

| A customer writes | What they get | Ready? |
|---|---|---|
| "I have a burst pipe" | A message to call the owner right away, with the business number | ✅ |
| "How much is a water heater replacement?" | An offer of a callback, since that price isn't on the business's pages | ✅ |
| "Do you sell pizza?" | A reply that points them back to plumbing, since that isn't a plumbing question | ✅ |
| "Are you open Saturdays?" | A short answer from the Hours & FAQ page | ✅ |

What each kind of message gets back is in [How the assistant behaves](docs/behaviour.md).

## How a message is handled

```mermaid
flowchart LR
    msg([Customer message]) --> one["1 · Spot an emergency"]
    one -->|urgent| call([Please call us now])
    one -->|not urgent| two["2 · Read the pages"]
    two --> three["3 · Write the answer"]
    three --> four["4 · Check every price"]
    four -->|prices match| reply([Reply goes out])
    four -->|unknown price| back([We'll call you back])
```

An emergency is caught first. A price is checked last. A number the pages don't state, or a price for a different service, does not go out.

## Where we are

- ✅ **Reads the pages:** all six, with the words a visitor actually sees.
- ✅ **Spots emergencies:** the urgent words get the fixed reply, right away.
- ✅ **Guards every price:** an amount is kept only when the pages state it near the service asked about. Any other amount is swapped for the callback reply.
- ✅ **Writes the answer:** a short reply from the business's pages.
- ✅ **Demo chat:** a page to try the same replies, from a link.
- ✅ **Handover:** [what you have, and how to change it yourself](docs/handover.md).

## Built with AI, checked by people

- **Clear roles.** Each change is planned, checked by tests, and reviewed before it goes live.
- **One change at a time.** Each change starts as a written request, with a plain-English summary.
- **Promises are tested.** The 16 agreed questions, the urgent words, and the price rules are tested on every change.
- **A person signs off.** Nothing is added until that sign-off is done.

## Take a closer look

- [What we've agreed](docs/agreements.md): the pages, the urgent words, the contact details, and the 16 test questions.
- [How the assistant behaves](docs/behaviour.md): what a customer gets back.
- [How the assistant works](docs/how-it-works.md): the path of a message, and how to try the sample site.
- [Setup guide](docs/setup-guide.md): how to run it.
- [Handover notes](docs/handover.md): what you have, and how to change it yourself.
- [Live test results](docs/test-results.md): the 15 questions and the urgent words, from the live demo on Nov 4.

**Next up:** the owner's notes from the demo call.
