# Handover notes

This page is for the owner, and for Carla, who edits the agreements. It says what you have, what is still open, and how to change the urgent words or a fixed reply yourself.

## What you have

- [What we've agreed](agreements.md): the pages, the urgent words, the contact details, and the 15 test questions.
- [How the assistant behaves](behaviour.md): what a customer gets back.
- [How the assistant works](how-it-works.md): the path of a message.
- [Setup guide](setup-guide.md): how to run it, including the [versions it was tested on](setup-guide.md#versions-it-was-tested-on).
- [Live test results](test-results.md): the 15 questions and the urgent words, from the live demo on Nov 4.
- [Project guide](../AGENTS.md): where things are, and how a change is made.
- [Agent setup](../.cursor/team/README.md): the roles the agents work in. The rules for how they work are in [working in this repo](../.cursor/rules/working-in-this-repo.mdc).
- The checks. From the project folder, run `python3 scripts/run_checks.py`. How to run them is in [Try it yourself](how-it-works.md#try-it-yourself).

## The live demo

The live demo is at [maple-demo.roxanatapia.dev](https://maple-demo.roxanatapia.dev). It is hosted for 14 days after delivery.

## Your Claude key

The Claude key is on your own Anthropic account, with a spend limit you set there. The costs are yours, and you can see them on that account. The key is not written in this project, and replies never show it. How to set it is in [Your Claude key](setup-guide.md#your-claude-key). Never put the key in the project or in a chat.

## Change it yourself

The code reads `docs/agreements.md` on every message. The urgent words are the bold phrases under the heading Urgent messages. A spelling written as `(also leaking)` right after a bold word counts as that word. The fixed reply is the line that starts with `>`. You do not edit the code to change the words or that reply.

You need to be signed in to GitHub, and you need permission to edit this project. How the project is shared or transferred is in [Handing over the code](setup-guide.md#handing-over-the-code).

1. Open this project on GitHub, then open the file `docs/agreements.md`.
2. Click the pencil, **Edit this file**. Stay on Edit, so you can see the plain text. The bold words look like `**burst pipe**`. The reply is the line that starts with `>`.
3. Under the heading Urgent messages, change the bold words or the reply line. Leave the heading as it is. To add a spelling, keep it in parentheses right after the word, as `(also leaking)`.
4. Click **Commit changes**. A commit is the saved edit. Write a short note about what you changed. Choose **Create a new branch for this commit and start a pull request**. A branch is a separate copy of the project, so this edit does not mix with anything else. Give the branch a plain name, such as `change-urgent-words`. Do not commit straight to the main branch. The checks run on a pull request. They do not run on a save straight to the main branch.
5. Click **Propose changes**. GitHub opens the pull request page. A pull request is the proposal to add your branch. Click **Create pull request**.
6. Wait on that page. The checks start on their own. A green check means it passed. A red check means it did not match.
7. When every check is green, a person reviews the change. Then click **Merge pull request**, and **Confirm merge**. Merge means the change joins the project.

After you save, the edit sits on the new branch. The main project is unchanged until you merge. The live assistant does not change when you save, and it does not change when you merge. The live assistant changes only once the merged change is deployed. Deployed means the live copy is updated from the merged project.

On a computer that already has the merged project, the next message uses the new words. The code reads the agreements file every time.

A red check means that check did not match, so the change is not ready. Do not merge it.

1. Open the red check and read its name. The name says what did not match.
2. If the heading, the bold words, or the `>` line was lost, edit `docs/agreements.md` again on the same branch and commit there. The checks run again.
3. If the file is shaped correctly and a check is still red, the check itself has to be changed. See the list below. That is a change to the checks, not to the code. Leave the pull request open until that check is updated and the checks are green.

Changing the fixed reply does not need a change to the code or the checks, if you keep all of this:

- The heading stays Urgent messages, and the reply stays on a line that starts with `>`.
- The reply still has a phone number written like (856) 555-0142, and it has no dollar sign.
- The reply stays a different sentence from the callback reply and the outage reply.
- The whole reply is not already written on the behaviour page, the README, or the how-it-works page.

Adding a new bold word does not need a change to the code. A check goes red, and the check has to be changed, if that word already appears on the behaviour page, even inside a longer word, or if it appears in an ordinary test question. An ordinary question would then be treated as urgent. Question 10, "I have a burst pipe. What should I do?", has to keep an urgent word in it.

Removing or renaming one of these words makes a check go red. The code does not need a change. The check does, because the check names the word: water everywhere, basement, leak, leaking, frozen pipe, burst pipe, and no heat. Leaking is the extra spelling on leak. "I have a leaky faucet" and "frozen pipes" are meant to stay not urgent. If either one becomes urgent, a check goes red and that check has to be changed.

The callback sentence, the off-topic reply, and the outage sentence are read from this same file. The checks expect those three sentences to stay word for word. Changing one of them does not need a change to the code, but it does need the check updated. The other edits in the agreements are listed in [Change what it says](setup-guide.md#change-what-it-says).

You can run the same checks on a computer before you merge. From the project folder, run `python3 scripts/run_checks.py`. OK means they passed. A failure ends with FAILED and names the check. The same steps are in [Check it still works](setup-guide.md#check-it-still-works).

## Known limits

- Misspelled service names, and a price written without a `$` sign, are still open. A small misspelling of a service does not get that service's answer. A price with no `$` can get a reply that talks about the customer, instead of to them. Details are in [#57](https://github.com/RoxanaTapia/maple-street-front-desk/issues/57).
- The owner is not told when a page can't be read. The customer is asked to call, and the assistant does not guess. Only a failed call to Claude is written in the owner's notes. Details are in [#58](https://github.com/RoxanaTapia/maple-street-front-desk/issues/58).

## Open question

Which phone number the call-us replies should show is still open. They use the main line from the agreements today. Please confirm that number, or say if a different one should be shown. Details are in [#59](https://github.com/RoxanaTapia/maple-street-front-desk/issues/59).

## Working with the agents

One issue, one branch, one pull request. The checks run, then a person reviews, and then you merge. An issue is the written request. A branch is a separate copy of the project. A pull request is the proposal to add that copy. The full steps are in [How a change happens](../AGENTS.md#how-a-change-happens).
