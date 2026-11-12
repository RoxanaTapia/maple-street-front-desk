# Handover notes

Dave and Carla, this page is yours. Everything you have lives in this project.

Live demo: [maple-demo.roxanatapia.dev](https://maple-demo.roxanatapia.dev), online until Wed Nov 25, 2026.

## Use it

- [maple-demo.roxanatapia.dev](https://maple-demo.roxanatapia.dev), until Wed Nov 25, 2026
- How to run it and change it: [Walkthrough](https://youtu.be/nhAtGt-w8D4)

## Run or change it

- [Setup guide](setup-guide.md)
- On your account, never stored here: [Your Claude key](setup-guide.md#your-claude-key)
- [How to change the urgent words](#change-the-urgent-words)

## Reference

- [What we've agreed](agreements.md), including the [16 test questions](agreements.md#the-16-test-questions)
- [Live test results](test-results.md)
- [How the assistant behaves](behaviour.md)
- [How the assistant works](how-it-works.md)
- [Project guide](../AGENTS.md)
- On every change: [Checks](how-it-works.md#try-it-yourself)

<details>
<summary>Working with the agents, and what the checks look for</summary>

Each change is one issue, one branch, and one pull request. The checks run, a person reviews, and then you merge.

The steps are in [How a change happens](../AGENTS.md#how-a-change-happens). The [roles](../.cursor/team/README.md) and [rules](../.cursor/rules/working-in-this-repo.mdc) are there too.

If a check turns red, open it. Its name says what did not match. Fix the agreements page on the same copy. The checks run again. If the file looks right, ask Roxana. The check itself may need updating.

You can change the urgent reply freely if:

- it stays on a line starting with `>`
- it keeps a phone number written like (856) 555-0142 and has no `$`
- it's different from the callback and outage replies
- it isn't already written word for word on the behaviour page, the README or the how-it-works page

| Edit | Needs a check update? |
|---|---|
| Remove or rename "water everywhere", "basement", "leak", "leaking", "frozen pipe", "burst pipe", or "no heat" | Yes |
| A new word that appears on the behaviour page, even inside a longer word, or in an ordinary test question | Yes |
| A change that makes "I have a leaky faucet" or "frozen pipes" urgent | Yes |
| Change the callback sentence, the off-topic reply, or the outage sentence | Yes |

</details>

## Not done yet

Settled on the call: call-us replies use your [main line](agreements.md#main-line-and-contact).

- Call-us replies cannot be edited on the agreements page alone. [#65](https://github.com/RoxanaTapia/maple-street-front-desk/issues/65)
- Misspellings, or prices with no `$`, can still go wrong. [#57](https://github.com/RoxanaTapia/maple-street-front-desk/issues/57)
- You won't get an alert if the assistant stops working. [#58](https://github.com/RoxanaTapia/maple-street-front-desk/issues/58)

## Keeping it live

After the 14-day demo, the assistant needs a home to stay live for your customers. Your team hosts it by following the [setup guide](setup-guide.md), and I include one free 30-minute walkthrough call with whoever sets it up.

## Change the urgent words

You edit a copy, then approve it.

1. Open [docs/agreements.md](agreements.md) and click **Edit this file**.
2. Change a bold word or the `>` reply, and keep the `>`.
3. **Commit changes**, name a branch, then **Propose changes**.
4. Click **Create pull request**.
5. Wait until every check is green.
6. Click **Merge pull request**, then **Confirm merge**.

If a check turns red, don't merge; ask Roxana in the PR.

## Who to ask

Ask Roxana on the pull request or in Upwork messages, until the demo goes offline.
