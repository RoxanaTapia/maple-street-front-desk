# How the assistant works

This page is for the people building the assistant, and for you, Dave, when you want to try it. Use it to start the sample site, run the checks, and follow one customer message from the moment it arrives to the reply. What a customer actually receives is in [How your assistant behaves](behaviour.md). The short picture is the [README](../README.md).

## Try it yourself

You need Python 3. From the project folder, open a terminal and start the sample site:

```
python3 scripts/serve_sample_site.py
```

It prints `Serving the sample site at http://127.0.0.1:8000`. Open that address. If the port is already in use, it prints `The sample site is already running on port 8000. Stop it with Ctrl+C, or start on another port with --port.` Leave the site running, and use a second terminal for the commands below. Stop the site with Ctrl+C.

Use single quotes when a message contains a dollar sign, so the shell keeps the amount. The commands for one message are in the sections below.

Run every check with:

```
python3 scripts/run_checks.py
```

Each check prints ok, and the run ends with OK. The same checks run on every pull request. To run one area:

- `python3 scripts/run_checks.py tests/test_checks.py`
- `python3 scripts/run_checks.py tests/test_links.py`
- `python3 scripts/run_checks.py tests/test_pages.py:PageListChecks`
- `python3 scripts/run_checks.py tests/test_pages.py:QuestionCoverageChecks`
- `python3 scripts/run_checks.py tests/test_urgent.py:UrgentReplyChecks`
- `python3 scripts/run_checks.py tests/test_prices.py:PriceChecks`
- `python3 scripts/run_checks.py tests/test_prices.py:LongerPriceChecks`
- `python3 scripts/run_checks.py tests/test_answers.py:AnswerChecks`

## The journey of a message

Every message takes the same path, in this order:

```mermaid
flowchart LR
    msg([Customer message]) --> one["1 · Spot an emergency"]
    one -->|urgent| call([Please call us now])
    one -->|not urgent| two["2 · Read your pages"]
    two --> three["3 · Write the answer"]
    three --> four["4 · Check every price"]
    four -->|prices match| reply([Reply goes out])
    four -->|unknown price| back([We'll call you back])
```

| | What happens | Script | Ready? |
|---|---|---|---|
| 1 | Spot an emergency | `scripts/urgent_reply.py` | Yes |
| 2 | Read your pages | `scripts/read_pages.py` | Yes |
| 3 | Write the answer | `scripts/answer_reply.py` | Shared parts |
| 4 | Check every price | `scripts/price_reply.py` | Yes |

An emergency stops at the first stop: the customer is asked to call, and nothing else runs. Every other message is answered from your pages, and the answer only goes out once every price in it matches what you've published. One command, `scripts/front_desk.py`, runs that whole path.

## 1 · Spot an emergency

An emergency should get a phone call, not a paragraph about opening hours. An urgent message is handled before anything else.

**Urgent messages get the fixed reply**

This part looks for the urgent words we agreed in [Urgent messages](agreements.md#urgent-messages). Those words, and the reply that goes with them, are read from that same place. When one of the words is there, the customer gets only the fixed urgent reply: nothing before it, nothing after it, and your pages are not read. A normal question is not treated as urgent. The phone number inside that reply is not a price. Checking a message prints the fixed reply when it is urgent, and says it is not when it is not.

```
python3 scripts/urgent_reply.py 'I have a burst pipe'
python3 scripts/urgent_reply.py 'Are you open Saturdays?'
```

You'll see:

1. The fixed urgent reply.
2. `This message is not urgent.`

## 2 · Read your pages

The assistant can only answer from what you've published, so it first reads the six pages listed in [Your pages](agreements.md#your-pages). It opens each one over the web, the way a browser would, and keeps the title and the words a customer can see. Code and styling are left out.

**Your pages are read**

All six pages are read, and each title matches its page. A page that can't be opened stays on the list as unreadable, with the reason, and the others are still read. Nothing is dropped quietly. The list shows the name, the title, the address, and whether the page was read. Every page shows the banner that this business is fictional. The sample pages use your phone number and the name Carla.

```
python3 scripts/read_pages.py
```

You'll see `Page list`, then Home, Services, Pricing, Service Area, Hours & FAQ, and Contact. Each has `Status: read`. The titles are Home | Maple Street, Services | Maple Street, Pricing | Maple Street, Service Area | Maple Street, Hours & FAQ | Maple Street, and Contact | Maple Street.

## 3 · Write the answer

A question should get a short answer from your pages, not a guess.

**Answers come from your pages**

Every question your pages answer gets a short answer that names the page it came from. Every question your pages don't cover gets the callback reply from [When the pages don't say](agreements.md#when-the-pages-dont-say). An urgent message stops before the pages are read. An amount that isn't on your pages is replaced with the callback reply.

The instructions for that answer include the text of your pages and the callback reply. They say to answer only from these pages, keep it short, name the page, and use that callback sentence when the pages don't cover the question.

You see this check on the pull request as Answers come from your pages.

`scripts/front_desk.py` runs the four parts in order: the urgent reply, then your pages, then this answer, then the price check. The real AI call waits until you choose the setup. Until then, the checks use a stand-in that answers the agreed test questions. It is not a real AI.

**Every test question has an answer plan**

The 15 questions in [The 15 test questions](agreements.md#the-15-test-questions) fall into three groups. A question your pages answer names the page it comes from. A question with a set reply uses the urgent reply, or offers a callback. A question that is still yours to decide offers a callback until you say otherwise. The drain-cleaning question is answered from Pricing. Hours says Sunday is closed, and Contact says how to book or cancel.

```
python3 scripts/answer_reply.py 'Are you open Saturdays?'
python3 scripts/front_desk.py 'How much is a drain cleaning?'
python3 scripts/front_desk.py 'Do you cover Moorestown?'
python3 scripts/front_desk.py 'I have a burst pipe'
```

You'll see:

1. `Saturday: 8:00 am to 12:00 pm. Yes, we are open Saturdays. From Hours & FAQ.`
2. `A drain cleaning is $149. From Pricing.`
3. The callback reply.
4. The fixed urgent reply.

## 4 · Check every price

The AI could make up a price, so every answer is checked before it goes out. Each money amount must appear on your pages exactly as written. If even one doesn't, the whole answer is replaced with the callback reply.

**Prices come only from your pages**

A price written on your pages is left as written. Before an answer is shown, each amount in it is kept only as it is written there. An amount that isn't on your pages is replaced with the callback reply. An answer with no amount is left as it is, and an urgent message is still handled first.

**A longer price isn't mistaken for a shorter one**

An amount is read whole, so $1499 is not treated as $149, and $149 at the end of a sentence is still $149. An answer of "A water heater is $1499." is replaced with the callback reply. "We're at 149 Maple Street" is left as it is, because an address is not a price.

`scripts/price_reply.py` takes an answer, the words the assistant would say, not a customer question. The whole path runs this check after the answer is written. You can still try one answer on its own:

```
python3 scripts/price_reply.py 'A drain cleaning is $149.'
python3 scripts/price_reply.py 'The call-out fee is 99 dollars.'
python3 scripts/price_reply.py 'A water heater replacement is $1,200.'
```

You'll see:

1. `A drain cleaning is $149.` It's unchanged, because your Pricing page says $149.
2. The callback reply. Your Services page writes the fee as $99, and "99 dollars" doesn't match it exactly.
3. The callback reply. Pricing doesn't list a water heater replacement.

## Still to come

- **The real AI call**, once you choose the setup. The instructions, the page name, the callback, and the path a message takes are already in place.
- **Matching each price to the right service.** A published amount is kept. The check does not yet confirm that the amount belongs to the service in the question.
- **More ways of writing prices.** Today "99 dollars" and "$149.00" get the callback reply, and "250 bucks" isn't read as a price.
- **Your OK on the 15 test questions and urgent words**, already written in [What we've agreed](agreements.md).
- **A demo link you can try**, then a setup guide and handover notes so you can run it yourself.
