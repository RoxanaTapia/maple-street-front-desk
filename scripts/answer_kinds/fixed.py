"""Read the fixed replies from the agreements."""

import agreed


def callback_reply(text=None):
    """Return the callback sentence from your agreements."""
    return agreed.callback_reply(text)


def outage_reply(text=None):
    """Return the outage sentence from your agreements."""
    return agreed.outage_reply(text)


def off_topic_reply(text=None):
    """Return the off-topic sentence from your agreements."""
    return agreed.off_topic_reply(text)


def discount_reply(text=None):
    """Return the discount sentence from your agreements."""
    return agreed.discount_reply(text)


def unlisted_service_reply(text=None):
    """Return the sentence used when the pages don't list that service."""
    return agreed.unlisted_service_reply(text)
