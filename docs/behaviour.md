# How the assistant behaves

| A customer writes | What they get |
|---|---|
| A question the business's pages answer | A short answer that ends by naming the page it used (From `<Page>`.) |
| A question the business's pages don't cover | The callback reply in [When the pages don't say](agreements.md#when-the-pages-dont-say) |
| A question that is clearly about something else | The off-topic reply in [Off-topic questions](agreements.md#off-topic-questions) |
| The assistant can't look that up | The outage reply in [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up), and nothing else |
| An urgent message | The fixed urgent reply, and nothing else. The business's pages are not read |
| A price | The amount as the business's pages write it, when it is on the same page and near the service asked about, or the callback reply |
| A wrong price | The price from the pages, spoken to the person, when the reply already states that price. A note that only talks about the customer is left out when its facts are already in a sentence that stays. A fact stated only in that note is kept. Agreeing with the wrong amount, or naming another amount, still gets the callback reply |

Only the listed urgent words trigger the urgent reply. A spelling named beside a listed word counts as that word. A question that mentions emergencies without one of them gets a normal answer. A question that is clearly about something else gets the off-topic reply. A question we do not recognize, including a plumbing or payment question the pages don't answer, still gets the callback reply.

The same words inside quotes, or with markdown marks around the whole question, get that same reply. A question mark on the end does not change it. A dollar sign, a decimal point, and a hyphen in the message stay as written.
