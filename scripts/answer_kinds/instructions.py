"""Build the instructions for one question."""

from answer_kinds.fixed import callback_reply
from answer_kinds.pages import _source_example

# The rule Claude is given. Speak to the person, and leave their amount out.
# The example is the sentence on the Pricing page.
CORRECT_A_WRONG_PRICE = (
    "If they state a price that differs from the pages, speak to them directly "
    "and give the price from the pages, for example: A drain cleaning is $149. "
    "Do not mention the customer, and do not repeat their price."
)


# A listed price is enough. The pages do not have to say "we do" as well.
PRICED_SERVICE_IS_OFFERED = (
    "If a service has a price on these pages, that service is offered. "
    "Say yes, include that price, and name the page."
)


# A small slip in a service name still means that service.
MISSPELLED_SERVICE = (
    "A small misspelling of a service on these pages still means that service. "
    "Answer as you would for the right spelling, in plain words."
)


# The price may be written without a dollar sign. Speak to the person.
PLAIN_PRICE = (
    "If they write a price without a dollar sign and it matches these pages, "
    "answer with a short yes that includes the price as the pages write it. "
    "Speak to them directly, and do not mention the customer."
)


# A yes or no question that states the wrong amount gets a clear no.
WRONG_AMOUNT_GETS_A_NO = (
    "If they ask a yes or no question and state a price that differs from the pages, "
    "say no, give the price from the pages, and do not say yes."
)


# How much is not a yes or no question.
HOW_MUCH_IS_NOT_YES = "If they ask how much, give the price from the pages with no leading yes."


# How, what, when, and where start with the fact.
FACT_FIRST = (
    "If they ask how, what, when, or where, start with the fact and do not add Yes. "
    "Add Yes only when they ask a yes or no question, such as are you, do you, or can I."
)


# A note is for the owner. It must not be written into the reply.
NO_INTERNAL_NOTE = "Do not add an internal note. The reply is only what the customer should read."


# Hours from one page and a booking line from another still name both.
NAME_EVERY_PAGE = (
    "When the answer uses facts from more than one page, name every page. "
    "For example, From Hours & FAQ and Contact."
)


def build_instructions(question, pages, text=None):
    """Build the instructions an AI would be given for this question."""
    callback = callback_reply(text)
    example = _source_example(pages)
    lines = [
        "Answer the customer's question only from these pages.",
        "Keep the answer short.",
        "Name the page the answer came from.",
        "End the answer with exactly From <Page name>.",
        f"For example, From {example}.",
        NAME_EVERY_PAGE,
        CORRECT_A_WRONG_PRICE,
        PRICED_SERVICE_IS_OFFERED,
        MISSPELLED_SERVICE,
        PLAIN_PRICE,
        WRONG_AMOUNT_GETS_A_NO,
        HOW_MUCH_IS_NOT_YES,
        FACT_FIRST,
        NO_INTERNAL_NOTE,
        "When the pages don't cover the question, reply with exactly this sentence:",
        callback,
        "",
        f"Customer question: {question}",
        "",
        "Pages:",
    ]
    for page in pages or []:
        name = page.get("name", "")
        if page.get("status") == "read":
            body = page.get("text") or ""
        else:
            reason = page.get("reason") or "unreadable"
            body = f"(unreadable: {reason})"
        lines.append(f"Page: {name}")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
