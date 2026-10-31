# How the assistant behaves

This is what a customer experiences. The words you have agreed are in [What you've agreed](agreements.md). This page does not copy them.

## How your pages are read

1. Which pages: only the pages listed in [What you've agreed](agreements.md#pages-the-assistant-answers-from).
2. Fetching: each page is fetched over the web, the way a browser would. Pricing is read with the other pages. If a page can't be fetched, it stays on the list and is marked unreadable with the reason. Nothing is skipped silently.
3. Reading: the page title and visible text are taken from each page. Scripts and styling are ignored.
4. Page list: each page is listed with its name, title, address, and status.

This step only reads your pages; answers come in a later step.

## How it works

An urgent message is checked before any answer.

1. The customer's message is checked for the [urgent words](agreements.md#urgent-words).
2. Those words and the [fixed urgent reply](agreements.md#fixed-urgent-reply) are read from [What you've agreed](agreements.md).
3. When the message contains one of those words, the reply is only that fixed reply. Nothing comes before it or after it, and your pages are not read.
4. Other wording is not treated as urgent.
5. The phone number in that reply is not a price.

## How the checks prove it

Every change runs these automatically, and the pull request's checks box shows each as a checklist. The page checks are in [tests/test_pages.py](../tests/test_pages.py). The urgent reply check is in [tests/test_urgent.py](../tests/test_urgent.py).

**Your pages are read**

- Pricing is live, so all six pages are read. Each title matches the page and includes the page's name.
- A page that can't be fetched stays on the list as unreadable, with the reason, and with no title. The other pages are still read.
- Scripts and styling are left out of the title and the visible text.
- Every page shows the banner that this business is fictional, and that banner is not hidden.
- Every agreed page appears on the page list, in order, with its title, address, and status. In your agreements, all six pages are agreed.
- Services names tankless water heaters and same-day service. Hours & FAQ names Saturday and financing. Service Area names Cherry Hill. Pricing names drain cleaning. Only Pricing shows a price. This does not check that the assistant answers.
- The sample pages use only the agreed phone number, (856) 555-0142, and they name Carla. No email address is included, and the contact page shows that phone number and Carla.
- Reading the pages prints a page list, with each page's name and address, and every page read. With no address, the list uses the local sample site. Asking for help shows how to run it.

**Every test question has an answer plan**

- All 15 test questions have a status, and each status is exactly one of these: answered by the pages, the callback reply, needs your answer, or the fixed urgent reply. The first six stay draft. The other nine are proposed, to confirm with you, with nine questions for you. An answered question points at an agreed page. The others name no page. The drain-cleaning answer is the price on Pricing. The hours page says Sunday is closed, and the contact page says how to book or cancel.

**Urgent messages get the fixed reply**

- Each urgent word gets the fixed reply, and nothing else.
- A normal question is not treated as urgent.
- The words and the reply are read from your agreements.
- An urgent message does not read your pages.
- The phone number in the urgent reply is not treated as a price.
- Checking a message prints the fixed reply when it is urgent, and says it is not when it is not.
- You see this check on the pull request as Urgent messages get the fixed reply.

## Answers

- Answer only from the pages in [Pages the assistant answers from](agreements.md#pages-the-assistant-answers-from).
- Show the page the answer came from.
- When the pages do not say, offer a callback using the [callback reply](agreements.md#callback-reply).
- Do not guess, and do not add a fact that is not on those pages.

The answers we expect are the [test questions](agreements.md#test-questions).

## Prices

- When a price is written on a page, quote it exactly as written there.
- Never show a price that is not written on your public pages.
- When the pages do not give a price, use the [callback reply](agreements.md#callback-reply).
