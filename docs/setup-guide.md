# Setup guide
👋 For the office: this page is yours. No technical knowledge needed.

## 🚀 Running it

You get a front desk that answers your customers.
Installing means a developer sets it up for you once. That is not the office's job. Below, that person is called the installer.

1. Have your own Anthropic (Claude) account, and set a spend limit on it.
2. Share access to that account with the installer. You agree how on one live 30-minute walkthrough call (not a recorded video), and the installer confirms it to you in writing afterwards, so you do not have to remember it.
3. Open the chat and ask a question. A reply comes back.

🛠️ Installer: your steps are in the [developer guide](developer-guide.md#🧰-first-install).

## ✅ Trusting it

You can see that it is working.
The automated tests cover your agreed questions, urgent messages, and prices.
If something looks wrong, tell the person who installed it.

## ✏️ Changing it

You can update the hours, the FAQ, the prices, and the contact info yourself.

1. Open the page that holds those words: [Hours and FAQ](../sample-site/hours.html), [Prices](../sample-site/pricing.html), or [Contact](../sample-site/contact.html).
2. Click the pencil, change the words a visitor reads, then choose Propose changes. That is a pull request: a proposed change you make in the browser.
3. The automated tests run on it. It goes live only after it is approved and installed, which means the installer puts the approved change into your running front desk.

A bigger change is quoted as a new milestone.

---

🛠️ Installing or maintaining it? That is the developer guide, not this page: [developer guide](developer-guide.md).
