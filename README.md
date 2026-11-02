# Maple Street Front Desk

**A front desk that will answer from your own pages, tells urgent callers to ring you right away, and never quotes a price you haven't published.**

This is where you can follow your customer assistant as it's built: what it does, how far along it is, and how every change is checked before it reaches your customers. For now it works on a small practice copy of your site, so nothing touches your real one.

## What your customers get

| A customer writes | The assistant replies | Ready? |
|---|---|---|
| "I have a burst pipe" | "This sounds urgent. Please call us now on (856) 555-0142." | ✅ |
| "How much is a water heater replacement?" | "I can't confirm that from your pages." | ✅ |
| "Are you open Saturdays?" | A short reply from your Hours & FAQ page: open Saturday morning | ⏳ |

Once answers are in place, every answer will come from your published pages. If your pages don't say, the assistant says so instead of guessing. More examples are in [How your assistant behaves](docs/behaviour.md).

## How a message is handled

```mermaid
flowchart LR
    msg([Customer message]) --> one["1 · Spot an emergency"]
    one -->|urgent| call([Please call us now])
    one -->|not urgent| two["2 · Read your pages"]
    two --> three["3 · Write the answer (coming next)"]
    three --> four["4 · Check every price"]
    four -->|prices match| reply([Reply goes out])
    four -->|unknown price| back([We'll call you back])
```

Emergencies are caught first, so an urgent caller never waits for a written answer. Every reply is checked for prices last, so nothing goes out with a number you haven't published.

## Where we are

- ✅ **Reads your pages:** all six, with the words a visitor actually sees.
- ✅ **Spots emergencies:** the urgent words we agreed get the fixed reply, right away.
- ✅ **Guards every price:** an amount that isn't on your pages is swapped for the callback reply.
- ⏳ **Writes the answer:** a short reply from your pages.
- ⏳ **Demo link and handover:** a link you can try, then a simple guide for running it yourself.

## Built with AI, checked by people

Your assistant is built with the help of AI agents, each with a clear job, and every change is checked before it counts.

- **A team with clear roles:** one AI agent plans each change, another writes the checks, and another keeps these pages clear and up to date.
- **One change at a time:** each change starts as a written request and arrives with a plain-English summary of what it does and why.
- **Your promises are tested every time:** each of your 15 agreed questions has a plan, and the urgent and price rules are tested on every change. If anything we agreed would break, the change stops.
- **A person signs off:** nothing is added until I've reviewed it.

## Take a closer look

- [What we've agreed](docs/agreements.md): your pages, urgent words, contact details and the 15 test questions.
- [How your assistant behaves](docs/behaviour.md): what your customers will experience.
- [How the assistant works](docs/how-it-works.md): a step-by-step look at the journey of a message.

**Next up:** the answer step, then a demo link you can try yourself.
