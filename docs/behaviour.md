# How the assistant behaves

| A customer writes | What they get |
|---|---|
| A question the business's pages answer | A short answer that ends by naming the page it used (From `<Page>`.) |
| A reply that uses facts from more than one page | A short answer that names every page it used (From Hours & FAQ and Contact.) |
| A question about a service that has a price on the pages | A short yes that includes that price and ends by naming the page (From `<Page>`.) |
| A question the business's pages don't cover | The callback reply in [When the pages don't say](agreements.md#when-the-pages-dont-say) |
| A question that is clearly about something else | The off-topic reply in [Off-topic questions](agreements.md#off-topic-questions) |
| The assistant can't look that up | The outage reply in [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up), and nothing else |
| An urgent message | The fixed urgent reply, and nothing else. The business's pages are not read |
| A price | The amount as the business's pages write it, when it is on the same page and near the service asked about, or the callback reply |
| A wrong price | The price from the pages, spoken to the person, when the reply already states that price. A note that only talks about the customer is left out when its facts are already in a sentence that stays. A fact stated only in that note is kept. Agreeing with the wrong amount, or naming another amount, still gets the callback reply |
| A yes or no question that states the wrong price | A clear no that names the price from the pages, and the page. A wrong amount never gets a yes |
| A how much question | The price from the pages, with no leading yes, and the page |
| A how, what, when, or where question | The fact, with no leading yes, and the page |
| A how much question about a faucet problem, including a small misspelling | The same reply as the right spelling. No amount is given. The call-us number is included |
| A request to ignore the rules, or for a discount | The discount reply in [Discounts](agreements.md#discounts) |
| A service the pages don't list | The reply in [A service the pages don't list](agreements.md#a-service-the-pages-dont-list) |
| An email address the pages don't list | A short reply that the pages don't list an email address, then the callback reply. No note is added |
| A question in two parts, when the pages cover only one | The covered part, with its price and its page, then a line that the pages don't list the other part, with the call-us number. Nothing is invented |

The urgent words and the fixed urgent reply are in [Urgent messages](agreements.md#urgent-messages). Only those words trigger the urgent reply. A spelling named beside a listed word counts as that word. The two call-us sentences are in [When the pages don't say](agreements.md#when-the-pages-dont-say) and [When the assistant can't look it up](agreements.md#when-the-assistant-cant-look-it-up).

A price on the pages is enough to say that service is offered. The reply says yes, gives that price as the pages write it, and names the page. A small misspelling of a service the pages list still gets that service's answer, in plain words. A price written without a dollar sign, such as 150 or 150 dollars, is still a price. When the amount matches the pages, the reply is short and speaks to the customer. A yes or no question that states a different amount gets a clear no that names the real price, and a wrong amount never gets a yes. A how much question gets that price with no leading yes. A how, what, when, or where question starts with the fact. Yes is added only for a yes or no question, such as are you open, do you, or can I. A how much question about a faucet problem, including a small misspelling of that problem, gets the same reply as the right spelling. When the pages list no price, the reply names the problem, gives no amount, and gives the call-us number. An amount in the reply that the pages don't state still gets the callback reply. A request to ignore the rules, or for a discount the pages don't offer, gets the discount reply. A service the pages don't list gets a reply that says so, plus the call-us number. A question that asks for an email the pages don't list says so, then uses the callback reply, and no note is added. A question in two parts answers the part the pages cover, with its price and its page, and says the pages don't list the other part. An internal note is never part of a reply. Text that starts with Note: is left out. A reply that uses facts from more than one page names every page it used.
