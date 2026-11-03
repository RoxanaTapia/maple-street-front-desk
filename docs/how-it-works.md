# How the assistant works

The assistant checks a message for an emergency, answers from the business's pages, and sends the reply only when every price matches those pages.

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

| | What happens | Script | Ready? |
|---|---|---|---|
| 1 | Spot an emergency | `scripts/urgent_reply.py` | Yes |
| 2 | Read the pages | `scripts/read_pages.py` | Yes |
| 3 | Write the answer | `scripts/answer_reply.py` | Shared parts |
| 4 | Check every price | `scripts/price_reply.py` | Yes |

`scripts/front_desk.py` runs these four parts in order. Start the sample site first. [Try it yourself](#try-it-yourself) is at the end.

## 1 · Spot an emergency

*An emergency should reach the phone, not a paragraph about opening hours.*

**What it does**

- Reads the urgent words in [Urgent messages](agreements.md#urgent-messages), and the reply that goes with them.
- When one of those words is present, the customer gets only the fixed urgent reply. The pages are not read.
- A frozen pipe is one of those words, so a message such as "I think I have a frozen pipe" gets only the fixed urgent reply.
- A normal question is left for the next part.

**Try it**

```
python3 scripts/urgent_reply.py 'I have a burst pipe'
python3 scripts/urgent_reply.py 'I think I have a frozen pipe'
python3 scripts/urgent_reply.py 'Are you open Saturdays?'
```

| Message | What you get |
|---|---|
| I have a burst pipe | The fixed urgent reply |
| I think I have a frozen pipe | The fixed urgent reply |
| Are you open Saturdays? | `This message is not urgent.` |

*Good to know.* The phone number in the fixed urgent reply is not a price. A plural such as "frozen pipes" is left for the next part. The same is true of "burst pipes".

*Pull request checks:* **Urgent messages get the fixed reply**. **A frozen pipe gets the urgent reply**

## 2 · Read the pages

*An answer can only use what the business has published.*

**What it does**

- Reads the six pages listed in [What we've agreed](agreements.md#your-pages).
- Opens each one over the web and keeps the title and the words a visitor can see. Code and styling are left out.
- A page that can't be opened stays on the list as unreadable, with the reason. The others are still read.

**Try it**

```
python3 scripts/read_pages.py
```

1. `Page list`, then Home, Services, Pricing, Service Area, Hours & FAQ, and Contact.
2. Each page has `Status: read`.
3. The titles are Home | Maple Street, Services | Maple Street, Pricing | Maple Street, Service Area | Maple Street, Hours & FAQ | Maple Street, and Contact | Maple Street.

*Good to know.* Every sample page shows a banner that this business is fictional. The sample uses the business phone number and the name Carla.

## 3 · Write the answer

*A question gets a short answer from the business's pages, or the callback reply when they don't cover it.*

**What it does**

- A question the pages answer gets a short answer that names the page.
- A question the pages don't cover gets the callback reply from [When the pages don't say](agreements.md#when-the-pages-dont-say).
- The instructions include the text of the business's pages. They say to answer only from these pages, keep it short, and name the page.
- The 15 questions in [The 15 test questions](agreements.md#the-15-test-questions) each name a page, use the fixed urgent reply, or offer a callback.
- The owner's answers on septic systems, being licensed and insured, and after-hours callouts are recorded and marked as waiting for the Hours & FAQ page. Until that page says so, those questions get the callback reply.

**Try it**

*The first command is this step alone. The others run the whole path.*

```
python3 scripts/answer_reply.py 'Are you open Saturdays?'
python3 scripts/front_desk.py 'How much is a drain cleaning?'
python3 scripts/front_desk.py 'Do you cover Moorestown?'
python3 scripts/front_desk.py 'Do you install septic systems?'
python3 scripts/front_desk.py 'I have a burst pipe'
```

| Message | What you get |
|---|---|
| Are you open Saturdays? | `Saturday: 8:00 am to 12:00 pm. Yes, we are open Saturdays. From Hours & FAQ.` |
| How much is a drain cleaning? | `A drain cleaning is $149. From Pricing.` |
| Do you cover Moorestown? | The callback reply |
| Do you install septic systems? | The callback reply |
| I have a burst pipe | The fixed urgent reply |

*Good to know.* The real AI call waits until the setup is chosen. Until then, a stand-in answers the agreed test questions. It is not a real AI.

You see this check on the pull request as Answers come from your pages.

*Pull request checks:* **Answers come from your pages**. **Recorded answers still get the callback**

## 4 · Check every price

*A price goes out only when the business's pages state that amount.*

**What it does**

- A price the pages state is kept only as it is written there.
- Any other amount is replaced with the callback reply. An answer with no amount is left as it is, and an urgent message is still handled first.
- An amount is read whole, so $1499 is not treated as $149. An answer of "A water heater is $1499." is replaced with the callback reply.
- "We're at 149 Maple Street" is left as it is, because an address is not a price.

**Try it**

```
python3 scripts/price_reply.py 'A drain cleaning is $149.'
python3 scripts/price_reply.py 'The call-out fee is 99 dollars.'
python3 scripts/price_reply.py 'A water heater replacement is $1,200.'
```

| Answer | What you get |
|---|---|
| A drain cleaning is $149. | `A drain cleaning is $149.` |
| The call-out fee is 99 dollars. | The callback reply |
| A water heater replacement is $1,200. | The callback reply |

*Good to know.* "99 dollars" does not match "$99". Pricing does not list a water heater replacement.

*Pull request checks:* **Prices come only from your pages**. **A longer price isn't mistaken for a shorter one**.

## Still to come

- **The real AI call**, once the setup is chosen. The instructions, the page name, the callback, and the path a message takes are already in place.
- **Matching each price to the right service.** A published amount is kept. The check does not yet confirm that the amount belongs to the service in the question.
- **More ways of writing prices.** Today "99 dollars" and "$149.00" get the callback reply, and "250 bucks" isn't read as a price.
- **The owner's OK** on the 15 test questions and urgent words, already written in [What we've agreed](agreements.md).
- **The Hours & FAQ page.** The owner's answers on septic systems, being licensed and insured, and after-hours callouts are recorded in the agreements. Those questions get the callback reply until that page says them.
- **A demo link to try**, then a setup guide and handover notes.

## Try it yourself

Python 3 is enough. From the project folder:

```
python3 scripts/serve_sample_site.py
```

It prints `Serving the sample site at http://127.0.0.1:8000`. Open that address. If the port is already in use, it prints `The sample site is already running on port 8000. Stop it with Ctrl+C, or start on another port with --port.` Leave the site running, and use a second terminal for the commands. Stop the site with Ctrl+C.

Use single quotes when a message contains a dollar sign, so the shell keeps the amount.

Run every check with one command:

```
python3 scripts/run_checks.py
```

Each check prints ok, and the run ends with OK. The same checks run on every pull request.

<details>
<summary>Run one area</summary>

- `python3 scripts/run_checks.py tests/test_checks.py`
- `python3 scripts/run_checks.py tests/test_links.py`
- `python3 scripts/run_checks.py tests/test_pages.py:PageListChecks`
- `python3 scripts/run_checks.py tests/test_pages.py:QuestionCoverageChecks`
- `python3 scripts/run_checks.py tests/test_urgent.py:UrgentReplyChecks`
- `python3 scripts/run_checks.py tests/test_urgent.py:FrozenPipeChecks`
- `python3 scripts/run_checks.py tests/test_prices.py:PriceChecks`
- `python3 scripts/run_checks.py tests/test_prices.py:LongerPriceChecks`
- `python3 scripts/run_checks.py tests/test_answers.py:AnswerChecks`
- `python3 scripts/run_checks.py tests/test_answers.py:RecordedAnswerChecks`

</details>
