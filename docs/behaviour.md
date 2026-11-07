# How the assistant behaves

| A customer writes | What they get |
|---|---|
| A question the business's pages answer | A short answer that ends by naming the page it used (From `<Page>`.) |
| A question the business's pages don't cover | The callback reply |
| An urgent message | The fixed urgent reply, and nothing else. The business's pages are not read |
| A price | The amount as the business's pages write it, when it is on the same page and near the service asked about, or the callback reply |

Only the listed urgent words trigger the urgent reply. A spelling named beside a listed word counts as that word. A question that mentions emergencies without one of them gets a normal answer.

The same words inside quotes, or with markdown marks around the whole question, get that same reply. A question mark on the end does not change it. A dollar sign, a decimal point, and a hyphen in the message stay as written.
