# Setup guide

This gets your front desk answering customers, and shows you how to trust it and keep it current.

## 🚀 Running it

You get a front desk that answers your customers.

1. Add your Claude key from your Anthropic account, and set a spend limit there.
2. In the project folder, start it.
   ```
   export ANTHROPIC_API_KEY='...'
   python3 scripts/demo_chat.py
   ```
3. Open http://127.0.0.1:8080, type a message, and a reply comes back.

## ✅ Trusting it

You get confidence that the answers are right.

The automated tests cover your agreed questions, urgent messages, and prices. OK means they passed. If something looks wrong, the customer still gets a reply, and a note on that computer records the time and the kind of problem.

## ✏️ Changing it

You can keep the answers current yourself.

1. Change the hours, the FAQ, the prices, or the contact info a visitor reads.
2. Ask the question again.
3. A bigger change is quoted as a new milestone.
[📚 More detail for your developer](setup-guide-reference.md)
