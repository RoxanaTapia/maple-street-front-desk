# Handover notes

Dave and Carla, welcome. This page is yours after delivery: everything you have, where each thing is, and what is still open.

## Everything you have

| Item | What it is | Link |
|---|---|---|
| Repository | This project: the assistant, your pages, and these notes | [maple-street-front-desk](https://github.com/RoxanaTapia/maple-street-front-desk) |
| Live demo | The chat in a browser. Online until Wed Nov 25, 2026. See [When the demo goes offline](#when-the-demo-goes-offline). | [maple-demo.roxanatapia.dev](https://maple-demo.roxanatapia.dev) |
| Walkthrough video | How to run it, and how to change it | [Watch the walkthrough](https://youtu.be/nhAtGt-w8D4) |
| Setup guide | How to run it on your own computer, with the versions it was tested on | [Setup guide](setup-guide.md) |
| Agreements | The pages, the urgent words, the contact details, and the [15 test questions](agreements.md#the-15-test-questions) | [What we've agreed](agreements.md) |
| Outage clip | Sent with the delivery message. There is no copy of it in this project. | Sent with the delivery message |
| Behavior | What a customer gets back | [How the assistant behaves](behaviour.md) |
| How it works | The path of a message | [How the assistant works](how-it-works.md) |
| Test results | The 15 questions and the urgent words from the live demo on Nov 4 | [Live test results](test-results.md) |
| Project guide | Where things are, and how a change is made | [Project guide](../AGENTS.md) |
| Checks | Run automatically on every pull request. To run them yourself, see Try it yourself. | [Try it yourself](how-it-works.md#try-it-yourself) |
| Your Claude key | On your own Anthropic account, with your own spend limit. It's never stored in the project. | [Your Claude key](setup-guide.md#your-claude-key) |

## What's still open

Found after the feedback round. Not fixed yet.

| Item | What it is | Link |
|---|---|---|
| Say yes when a price is listed | If your pages list a price for a service, the assistant should say yes and give that price. Today, "Do you clean drains?" asks the customer to call. | [Say yes to a service when a price is listed](https://github.com/RoxanaTapia/maple-street-front-desk/issues/64) |
| Edit the call-us replies | The urgent words can be changed on the agreements page alone. The two "please call us" replies cannot be changed there alone yet. | [Edit the call-us replies on the agreements page alone](https://github.com/RoxanaTapia/maple-street-front-desk/issues/65) |
| Misspellings and prices without $ | A misspelled service name, or a price with no `$`, can still get the wrong reply. | [Misspellings and prices without $](https://github.com/RoxanaTapia/maple-street-front-desk/issues/57) |

The office isn't alerted when a page is down. That older limit is under [Known limits](#known-limits).

## When the demo goes offline

The live demo at maple-demo.roxanatapia.dev stays online until Wed Nov 25, 2026, 14 days after delivery. After that we take it offline.

What you keep is this repository, all the handover docs, and the checks.

To run it again yourself, follow [Try it on your computer](setup-guide.md#try-it-on-your-computer).

If you'd like us to keep it online for you, ask us for a quote.

## Change the urgent words

The assistant takes its urgent words and replies from the [agreements page](agreements.md), so editing that page on GitHub is how you change them.

A branch is a draft copy of the project. A pull request asks to add your draft to the live version.

1. On GitHub, open [docs/agreements.md](agreements.md) and click the pencil icon (**Edit this file**).
2. Under Urgent messages, change a word in bold, or the reply on the line that starts with `>`. Keep the `>` at the start.
3. Click **Commit changes**. Choose **Create a new branch**, name it, for example `change-urgent-words`, and click **Propose changes**.
4. On the next page, click **Create pull request**.
5. Wait a few minutes until every check shows a green tick.
6. Click **Merge pull request**, then **Confirm merge**.

> **Note:** After you merge, let Roxana know in a comment on the pull request. She updates the live assistant, and the change is live from then on.

## If a check turns red

Do not merge. Open the check. Its name says what did not match.

Fix `docs/agreements.md` on the same branch. The checks run again.

If the file looks right, ask Roxana in a comment on the pull request. The check itself may need updating.

<details>
<summary>What the checks look for</summary>

You can change the urgent reply freely if:

- it stays on a line starting with `>`
- it keeps a phone number written like (856) 555-0142 and has no `$`
- it's different from the callback and outage replies
- it isn't already written word for word on the behavior page, the README or the how-it-works page

| Edit | Needs a check update? |
|---|---|
| Remove or rename "water everywhere", "basement", "leak", "leaking", "frozen pipe", "burst pipe", or "no heat" | Yes |
| A new word that appears on the behavior page, even inside a longer word, or in an ordinary test question | Yes |
| A change that makes "I have a leaky faucet" or "frozen pipes" urgent | Yes |
| Change the callback sentence, the off-topic reply, or the outage sentence | Yes |

</details>

## Known limits

A misspelled service name, or a price with no `$`, can still get the wrong reply. [Issue: misspellings and prices without $](https://github.com/RoxanaTapia/maple-street-front-desk/issues/57)

The office isn't alerted when a page is down. [Issue: page-down alert](https://github.com/RoxanaTapia/maple-street-front-desk/issues/58)

## Settled on the handover call

The "please call us" replies show your [main line](agreements.md#main-line-and-contact). You confirmed that on the handover call, so the number stays as it is.

## Working with the agents

Each change is one issue, one branch, and one pull request. The checks run, a person reviews, and then you merge.

The steps are in [How a change happens](../AGENTS.md#how-a-change-happens). The [roles](../.cursor/team/README.md) and [rules](../.cursor/rules/working-in-this-repo.mdc) are there too.
