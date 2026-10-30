# Maple Street Front Desk

A front-desk assistant for Maple Street that answers your customers' questions only from your own pages. It will give urgent messages your main line right away and never quote a price you haven't published. For now it runs on a fictional sample site.

## What works now

- A [sample site](sample-site/) of six pages, including a readable Pricing page.
- The page reader and the page list. See [How your pages are read](docs/behaviour.md#how-your-pages-are-read).
- Four automatic checks. See [How the checks prove it](docs/behaviour.md#how-the-checks-prove-it).

## How it fits together

The page reader reads your agreed pages from the site and shows which ones it found. Automatic checks test this on every change.

```mermaid
flowchart LR
  agreed["Your agreed pages"] --> reader["Page reader"]
  site["Sample site"] --> reader
  reader --> list["Page list"]
  list -.-> answers["Answers (later step)"]
  checks["Automatic checks"] -. test .-> reader
  checks -. test .-> agreed
  style answers stroke-dasharray: 5 5
```

## What's planned

- Answers from your pages, in a later step. The drain-cleaning question will be answered from Pricing.
- [Agree on the 15 test questions and the urgent words](https://github.com/RoxanaTapia/maple-street-front-desk/issues/3), Sat Oct 31
- [Urgent messages get a fixed reply with your main line](https://github.com/RoxanaTapia/maple-street-front-desk/issues/4), Mon Nov 2
- [Never give a price that isn't on your pages](https://github.com/RoxanaTapia/maple-street-front-desk/issues/5), Mon Nov 2
- [Demo link and handover](https://github.com/RoxanaTapia/maple-street-front-desk/issues/6), Tue Nov 3 and Wed Nov 4

## Try it

1. In Cursor, open the project and a terminal (``Ctrl+` `` or `Cmd+J` on a Mac). You need Python 3.
2. Run `python3 scripts/serve_sample_site.py` and open the address it prints.
3. In a second terminal, run `python3 scripts/read_pages.py`. Every page is listed as read.

Stop the site with `Ctrl+C`.

## Where things are

- [What you've agreed](docs/agreements.md)
- [How the assistant behaves](docs/behaviour.md)
- [tests/](tests/): the automatic checks
- [AGENTS.md](AGENTS.md): how this project is built and changed
- [How your assistant gets built](https://github.com/RoxanaTapia/maple-street-front-desk/issues/1)
