# Handover notes

Dave and Carla, welcome. This page is yours.

It shows what you have, what is still open, and how you change the urgent words or the urgent reply.

You do that on GitHub. The program reads the agreements for you.

## ✅ At a glance

| Item | What it is | Link |
|---|---|---|
| Agreements | The pages, the urgent words, the contact details, and the 15 test questions | [What we've agreed](agreements.md) |
| Behaviour | What a customer gets back | [How the assistant behaves](behaviour.md) |
| How it works | The path of a message | [How the assistant works](how-it-works.md) |
| Setup | How to run it, with the versions it was tested on | [Setup guide](setup-guide.md#versions-it-was-tested-on) |
| Test results | The 15 questions and the urgent words from the live demo on Nov 4 | [Live test results](test-results.md) |
| Project guide | Where things are, and how a change is made | [Project guide](../AGENTS.md) |
| Agent setup | The roles the agents work in, and the rules they follow | [Roles](../.cursor/team/README.md), [rules](../.cursor/rules/working-in-this-repo.mdc) |
| Checks | From the project folder, run `python3 scripts/run_checks.py` | [Try it yourself](how-it-works.md#try-it-yourself) |
| Live demo | Hosted for 14 days after delivery | [maple-demo.roxanatapia.dev](https://maple-demo.roxanatapia.dev) |
| Claude key | On your own Anthropic account, with your own spend limit. Never stored in the project | [Your Claude key](setup-guide.md#your-claude-key) |

## 📝 Change it yourself

A branch is a separate copy of the project. A pull request is the proposal to add it.

1. On GitHub, open `docs/agreements.md` and click **Edit this file**.
2. Under Urgent messages, change a bold word, or the reply line that starts with `>`.
3. Click **Commit changes**, choose a new branch such as `change-urgent-words`, and start a pull request.
4. Click **Propose changes**, then **Create pull request**.
5. Wait until every check is green.
6. Click **Merge pull request**, then **Confirm merge**.

> **Note:** The live assistant updates only after the merged change is deployed.

## If a check turns red

Do not merge. Open the check. Its name says what did not match.

Fix `docs/agreements.md` on the same branch. The checks run again.

If the file looks right, ask Roxana. The check itself may need updating.

<details>
<summary>What the checks look for</summary>

| Edit | Needs a check update? |
|---|---|
| The urgent reply, kept on a `>` line, with a phone number like (856) 555-0142, no `$`, different from the callback and outage replies, and not already written on the behaviour page, the README, or the how-it-works page | No |
| Remove or rename water everywhere, basement, leak, leaking, frozen pipe, burst pipe, or no heat | Yes |
| A new word that appears on the behaviour page, even inside a longer word, or in an ordinary test question | Yes |
| A change that makes "I have a leaky faucet" or "frozen pipes" urgent | Yes |
| Change the callback sentence, the off-topic reply, or the outage sentence | Yes |

</details>

## Known limits

A misspelled service name, or a price with no `$`, can still get the wrong reply. [#57](https://github.com/RoxanaTapia/maple-street-front-desk/issues/57)

If a page can't be read, the customer is asked to call, and you are not told the page is down. [#58](https://github.com/RoxanaTapia/maple-street-front-desk/issues/58)

## Open question

Please confirm whether the call-us replies should keep the main line, or show a different number. [#59](https://github.com/RoxanaTapia/maple-street-front-desk/issues/59)

## Working with the agents

Each change is one issue, one branch, and one pull request. The checks run, a person reviews, and then you merge.

The steps are in [How a change happens](../AGENTS.md#how-a-change-happens).
