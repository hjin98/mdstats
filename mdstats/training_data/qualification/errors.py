"""Typed failures for V7-native post-production qualification.

Qualification is a downstream *consumer* of the accepted P1-P6 product.  Its
error vocabulary therefore distinguishes three genuinely different things: a
programming/lineage defect (hard error), a scientific verdict about the exact
frozen product (``rejected``), and an honestly incomplete external dependency
(``waiting_for_reference``).  Only the first is an exception; the other two are
terminal typed results and live in :mod:`.components`.
"""

from __future__ import annotations

from ..campaign_post_selection import PostSelectionError


class QualificationError(PostSelectionError):
    """A qualification path could not proceed truthfully."""


class QualificationLineageError(QualificationError):
    """Evidence, artifact bytes, or identities do not reauthenticate."""


class QualificationActivationError(QualificationError):
    """A one-shot locked activation precondition was violated."""


class QualificationUnavailableError(QualificationError):
    """A required real runtime/owner is unavailable, so nothing is claimed.

    This is deliberately *not* a scientific rejection: an absent supported
    deployment runtime says nothing about the product, and converting it into a
    pass or a reject would both be false.
    """


__all__ = [
    "QualificationActivationError",
    "QualificationError",
    "QualificationLineageError",
    "QualificationUnavailableError",
]
