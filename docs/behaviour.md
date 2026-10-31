# How your assistant behaves

This is what a customer experiences. Everything you've settled is in [What we've agreed](agreements.md). The words live there, so this page doesn't copy them.

## How your pages are read

The assistant reads only the pages named in [Your pages](agreements.md#your-pages). It opens each one over the web, the way a browser would, and keeps the title and the words a customer can see. Code and styling are left out.

If a page can't be opened, it stays on the list as unreadable, with the reason. Nothing is dropped quietly. The list shows the name, the title, the address, and whether the page was read.

Reading the pages comes first. Answers come in a later step.

## How it works

An urgent message is handled before anything else.

The message is checked for the words in [Urgent messages](agreements.md#urgent-messages). Those words, and the reply that goes with them, are read from that same place. When one of the words is there, the reply is only that fixed reply: nothing before it, nothing after it, and your pages are not read for it. Any other wording is left alone. The phone number inside that reply is not a price.

## How the checks prove it

Every change runs these checks on its own. On a pull request, each one shows up as a checklist.

**Your pages are read**

All six pages are read, and each title matches its page. A page that can't be opened stays on the list as unreadable, with the reason, and the others are still read. Code and styling stay out of the title and the visible text. Every page shows the banner that this business is fictional. The list follows your pages, with each name, title, address, and whether it was read. The sample pages use your phone number, name Carla, and include no email address.

**Every test question has an answer plan**

The 15 questions in [The 15 test questions](agreements.md#the-15-test-questions) fall into three groups. A question your pages answer names the page it comes from. A question with a set reply uses the urgent reply, or offers a callback. A question that is still yours to decide offers a callback until you say otherwise. The drain-cleaning question is answered from Pricing. Hours says Sunday is closed, and Contact says how to book or cancel.

**Urgent messages get the fixed reply**

Each urgent word gets the fixed reply, and nothing else. A normal question is not treated as urgent. The words and the reply are read from your agreements. An urgent message does not read your pages. The phone number in the urgent reply is not treated as a price. Checking a message prints the fixed reply when it is urgent, and says it is not when it is not. You see this check on the pull request as Urgent messages get the fixed reply.

**Prices come only from your pages**

A price written on your pages is left as written. An amount that isn't on your pages is replaced with the callback reply. An answer with no amount is left as it is. An urgent message is handled first. You see this check on the pull request as Prices come only from your pages.

## Answers

Answers come only from the pages in [Your pages](agreements.md#your-pages), and the assistant shows which page an answer came from. When the pages don't say, it offers a callback in the words from [When the pages don't say](agreements.md#when-the-pages-dont-say). It doesn't guess, and it doesn't add anything that isn't written there.

The answers we expect are the [15 test questions](agreements.md#the-15-test-questions).

## Prices

When a price is written on a page, the assistant quotes it as written. It never shows a price that isn't on your public pages. When the pages don't give a price, it uses the [callback reply](agreements.md#when-the-pages-dont-say).

Before an answer is shown, each amount in it is checked against your pages and kept only as it is written there. An amount that isn't on your pages is replaced with the callback reply, an answer with no amount stays as it is, and an urgent message is still handled first.
