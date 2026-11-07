# How the assistant behaves

| A customer writes | What they get |
|---|---|
| A question the business's pages answer | A short answer that ends by naming the page it used (From `<Page>`.) |
| A question the business's pages don't cover | The callback reply |
| A question that is not about plumbing | The off-topic reply in [Off-topic questions](agreements.md#off-topic-questions) |
| An urgent message | The fixed urgent reply, and nothing else. The business's pages are not read |
| A price | The amount as the business's pages write it, when it is on the same page and near the service asked about, or the callback reply |

Only the listed urgent words trigger the urgent reply. A spelling named beside a listed word counts as that word. A question that mentions emergencies without one of them gets a normal answer. A question that is not about plumbing gets the off-topic reply. A plumbing question the pages don't answer still gets the callback reply.
