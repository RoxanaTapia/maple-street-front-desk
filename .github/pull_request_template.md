Closes #N

<!--
Optional. One or two plain sentences right after Closes #N, saying why this step comes at this point in the plan.
-->

## 📝 What changes

<!--
Short bullets in plain English, one line each.
List the acceptance boxes from the issue that this change covers.
No links to test files. No internal notes, prices, hostnames, or tool footers.
When a change adds or changes a script, update its section in docs/how-it-works.md (what it does, why it's there, a command to try).
-->

- One change, in a sentence.

## ⚙️ How it works

<!--
Two or three plain sentences on why the change exists and what it does.
Start from the risk it handles, for example: "The AI can make up a price, so we check what it's about to say."
Then a "Not covered yet" list of at most a few one-line bullets naming which step covers each.
No implementation detail, no code terms.
-->

Why this change exists, and what it does, in two or three plain sentences.

Not covered yet:

- One gap, and the step that covers it.

## 🔍 How to review

<!--
Keep it concise.
Name the script or file to run, in backticks.
Give two or three ready-to-paste commands that show the expected result. Use single quotes around $ amounts.
Add one sentence on what each command should return.
Leave this whole section out when there's nothing to try by hand.
-->

One short reason to try it, and the file in backticks.

```
first command
second command
```

What each command returns, in one sentence.

## ✅ Checks

<!--
Link to this pull request's checks tab.
When they have passed, the link text is "All checks passed".
Each new check gets one bullet under the link: the check name in bold, a colon, then one plain line naming the cases it tries and what each gives.
Only new checks are listed below. Do not add How it was tested or Try it. No links to test files.
Guidance: **Prices come only from your pages:** $149 is shown, $1,200 gets the callback reply, and an answer with no price is left as it is.
-->

[All checks passed](https://github.com/RoxanaTapia/maple-street-front-desk/pull/N/checks)

- **Check name:** the cases it tries, and what each gives.
