# Setup guide

## Running it

You get a front desk that answers customers.

1. Use Python 3 from [.python-version](../.python-version).
2. Nothing else to install.
3. Get the client's Claude key from Anthropic.
4. Set a spend limit there.
5. Open a terminal in the project folder.
6. Put the key on that computer only.
   ```
   export ANTHROPIC_API_KEY='...'
   ```
7. Keep the key out of the project.
8. Keep the key out of replies.
9. Start the chat.
   ```
   python3 scripts/demo_chat.py
   ```
10. Open http://127.0.0.1:8080.
11. You should see `Demo chat at http://127.0.0.1:8080`.
12. The page says it is a demo.
13. Type a message.
14. A reply comes back.
15. Stop the chat with Ctrl+C.
16. The chat starts the pages for you.
17. No key means a stand-in, not the AI.

## Trusting it

You get confidence that the answers are right.

1. Run the automated tests.
   ```
   python3 scripts/run_checks.py
   ```
2. OK means every automated test passed.
3. FAILED names the automated test.
4. The automated tests cover the agreed questions.
5. They cover the urgent words.
6. They cover the price rule.
7. Keep a price only when stated near the service.
8. Fix the page, then run the automated tests again.
9. If Claude is down, or the key expired, the customer gets the outage reply.
10. Read `logs/error-notes.log` on the computer that runs the assistant.
11. A line has the time and the error kind.
12. It has no customer message or key.
13. If a page will not open, that question gets the callback sentence.
14. A question another page answers is still answered.

## Changing it

You keep the answers current yourself.

1. Change hours and FAQ in `sample-site/hours.html`.
2. Change prices in `sample-site/pricing.html`.
3. Change contact info on the site in `sample-site/contact.html`.
4. Edit reply contact lines on the agreements page, using the [handover notes](handover.md#set-your-call-us-number-and-your-emergency-number).
5. Ask the question again.
6. For a bigger change, ask Roxana.
7. A bigger change is quoted as a new milestone.

## Versions it was tested on

- The Claude model is `claude-haiku-5-5`.
- Change it with `CLAUDE_MODEL`.
- The API version is `2023-06-01`.
- Python 3.12 is for the automated tests.

Engineer notes: [setup guide reference](setup-guide-reference.md).
