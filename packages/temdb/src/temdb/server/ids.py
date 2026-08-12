import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
    """Return a time-ordered UUIDv7 as a stdlib uuid.UUID.

    UUIDv7 embeds a millisecond timestamp in its high bits, giving B-tree and
    partition-friendly index locality compared to v4.
    """
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
