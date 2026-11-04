# Live test results

Wednesday, Nov 4, 2026. Live demo: <https://maple-demo.roxanatapia.dev>. Version: main at commit e0a24d6.

**15 of 15 questions and 4 of 4 urgent words pass.**

We sent each question to the live demo one at a time, as a customer would, and checked every reply against what we agreed. Replies came back in under 2.2 seconds each.

## The 15 test questions

| # | Question | We agreed | Reply from the live demo | Pass |
|---|---|---|---|---|
| 1 | Do you service tankless water heaters? | Yes, from Services | "Yes, we service tankless water heaters. From Services." | ✅ |
| 2 | Are you open Saturdays? | Yes, 8:00 am to 12:00 pm, from Hours & FAQ | "Yes, we're open Saturdays from 8:00 am to 12:00 pm. From Hours & FAQ." | ✅ |
| 3 | How much is a drain cleaning? | $149, from Pricing | "A drain cleaning is $149. From Pricing." | ✅ |
| 4 | Do you cover Cherry Hill? | Yes, from Service Area | "Yes, we cover Cherry Hill. From Service Area." | ✅ |
| 5 | Can I get same-day service? | Yes, from Services | "Yes, we offer same-day service. The call-out fee is $99. From Services." | ✅ |
| 6 | Do you offer financing? | Yes, from Hours & FAQ | "Yes, we offer financing. From Hours & FAQ." | ✅ |
| 7 | Are you open Sundays? | No, closed, from Hours & FAQ | "No, we're closed on Sundays. From Hours & FAQ." | ✅ |
| 8 | How do I book or cancel an appointment? | Call the main line, from Contact | "To book or cancel, call the main line at (856) 555-0142. From Contact." | ✅ |
| 9 | How much is a call-out? | $99, from Services | "The call-out fee is $99. From Services." | ✅ |
| 10 | I have a burst pipe. What should I do? | The urgent reply | "This sounds urgent. Please call us now on (856) 555-0142." | ✅ |
| 11 | Do you cover Moorestown? | Callback reply | "I can't confirm that from your pages." | ✅ |
| 12 | How much is a water heater replacement? | Callback reply | "I can't confirm that from your pages." | ✅ |
| 13 | Do you install septic systems? | No, from Hours & FAQ | "No, we don't install or service septic systems. From Hours & FAQ." | ✅ |
| 14 | Are you licensed and insured? | Yes, in New Jersey, from Hours & FAQ | "Yes, we're fully licensed and insured in New Jersey. From Hours & FAQ." | ✅ |
| 15 | Do you offer after-hours emergency callouts? | Yes, call the main line, from Hours & FAQ | "Yes, we handle emergencies after hours too. Just call our main line at (856) 555-0142. From Hours & FAQ." | ✅ |

## Urgent words

Each of these got exactly the urgent reply: "This sounds urgent. Please call us now on (856) 555-0142."

| Urgent word | Message we sent | Pass |
|---|---|---|
| no heat | We have no heat in the house since this morning. | ✅ |
| burst pipe | There's a burst pipe in my basement. | ✅ |
| flooding | My kitchen is flooding, help! | ✅ |
| frozen pipe | I think I have a frozen pipe under the sink. | ✅ |

Urgent messages were answered in under a second. Every other reply took about 1.5 to 2 seconds.

## What the automatic checks cover

`python3 scripts/run_checks.py` runs 45 checks.

**Your pages (8):** The six practice pages are read, with the words a visitor sees, the agreed phone number, and a note when a page cannot be opened.

**Urgent problems (7):** Each urgent word, in any capitalisation, gets the call-now reply and nothing else, and a normal question does not.

**Prices (7):** A price is kept only when the pages state that amount as written, a longer amount is not read as a shorter one, and an address or a phone number is not a price.

**Answers (13):** A question the pages cover gets a short answer that ends with the page it used, and a question they do not cover, or a failed call, gets the callback reply.

**The demo chat (5):** The chat page says it is a demo, shows the reply as text, keeps the Claude key off the page, and sends when Enter is pressed.

**The project (5):** The project files are present, Python matches the recorded version, links in the docs point at real pages, and a proposed change runs these checks.

The checks use a stand-in instead of Claude, so they run in seconds at no cost, and the live results above use the real assistant.
