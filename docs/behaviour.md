# How the assistant behaves

| A customer writes | What they get |
|---|---|
| A question the business's pages answer | A short answer that ends by naming the page it used (From `<Page>`.) |
| A question about a service that has a price on the pages | A short yes that includes that price and ends by naming the page (From `<Page>`.) |
| A question the business's pages don't cover | The callback reply in [When the pages don't say](agreements.md#when-the-pages-dont-say) |
| A question that is clearly about something else | The off-topic reply in [Off-topic questions](agreements.md#off-topic-questions) |
| The assistant can't look that up | The outage reply in [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up), and nothing else |
| An urgent message | The fixed urgent reply, and nothing else. The business's pages are not read |
| A price | The amount as the business's pages write it, when it is on the same page and near the service asked about, or the callback reply |
| A wrong price | The price from the pages, spoken to the person, when the reply already states that price. A note that only talks about the customer is left out when its facts are already in a sentence that stays. A fact stated only in that note is kept. Agreeing with the wrong amount, or naming another amount, still gets the callback reply |

The urgent words and the fixed urgent reply are in [Urgent messages](agreements.md#urgent-messages). Only those words trigger the urgent reply. A spelling named beside a listed word counts as that word. The two call-us sentences are in [When the pages don't say](agreements.md#when-the-pages-dont-say) and [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up).

A price on the pages is enough to say that service is offered. The reply says yes, gives that price as the pages write it, and names the page. A small misspelling of a service the pages list still gets that service's answer, in plain words. A price written without a dollar sign, such as 150 or 150 dollars, is still a price. When the amount matches the pages, the reply is short and speaks to the customer. A wrong amount still gets the callback reply.
