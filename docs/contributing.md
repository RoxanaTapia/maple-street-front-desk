# Contributing

This page is for the people building the assistant.

## How to run it

You need Python 3. From the project folder, open a terminal.

1. Start the sample site with `python3 scripts/serve_sample_site.py` and open the address it prints. If that port is already in use, you'll see a short message telling you to stop the other copy with Ctrl+C, or to start again with `--port`.
2. In a second terminal, read the pages with `python3 scripts/read_pages.py`. Each page is listed as read. With no address, it uses the sample site you just started.
3. Try an urgent message with `python3 scripts/urgent_reply.py "I have a burst pipe"`. You should see the fixed urgent reply.
4. Try a normal question with `python3 scripts/urgent_reply.py "Are you open Saturdays?"`. You should see that it is not treated as urgent.
5. With the sample site still running, try a price from your pages with `python3 scripts/price_reply.py 'A drain cleaning is $149.'`. You should see that same sentence.
6. Try a price that isn't on your pages with `python3 scripts/price_reply.py 'A water heater replacement is $1,200.'`. You should see the callback reply.
7. Run every check with `python3 scripts/run_checks.py`.

`price_reply.py` takes an answer (what the assistant would say), not a customer question. Use single quotes when a message contains a dollar sign, so the shell keeps the amount.

Stop the site with Ctrl+C.

The same checks run on every pull request. To run one area:

- `python3 scripts/run_checks.py tests/test_checks.py`
- `python3 scripts/run_checks.py tests/test_links.py`
- `python3 scripts/run_checks.py tests/test_pages.py:PageListChecks`
- `python3 scripts/run_checks.py tests/test_pages.py:QuestionCoverageChecks`
- `python3 scripts/run_checks.py tests/test_urgent.py:UrgentReplyChecks`
