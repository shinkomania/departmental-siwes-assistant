"""
Academic Directory Identity Utilities
-------------------------------------

Provides deterministic normalization for DSA academic-directory identity.

These functions support duplicate prevention, controlled source imports,
alias matching and directory discovery. They do not determine whether two
records are authoritatively the same entity; ambiguous matches must still
be reviewed through the appropriate controlled workflow.
"""

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_directory_identity(value):
    """
    Return a stable comparison key for an academic-directory text value.

    Normalization deliberately remains conservative:
    - Unicode is normalized using NFKC;
    - surrounding whitespace is removed;
    - repeated internal whitespace is collapsed;
    - comparison is case-insensitive through casefold().

    Punctuation and meaningful words are intentionally preserved. More
    aggressive fuzzy/alias matching belongs to the discovery/import layer,
    not canonical database identity.
    """
    if value is None:
        return None

    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = _WHITESPACE_RE.sub(" ", normalized.strip())

    if not normalized:
        return None

    return normalized.casefold()


def normalize_optional_directory_identity(value):
    """
    Normalize an optional identity component to a non-null comparison key.

    This is useful for nullable identity components such as Programme.award,
    where a missing award must still participate deterministically in a
    composite uniqueness rule.
    """
    return normalize_directory_identity(value) or ""
