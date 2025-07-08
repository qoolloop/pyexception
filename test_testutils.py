# Copyright (C) 2025, Kan Torii (qoolloop).
"""Tests for `testutils` module."""

import pytest

from . import testutils
from .exception import (
    Reason,
    RecoveredException,
)


class OneReason(Reason):
    """Just one example of a reason."""


class AnotherReason(Reason):
    """Another example of a reason."""


class OneException(Exception):
    """Just one example of an exception."""


def test_raises__expected() -> None:
    """Test for `@testutils.raises` with expected exception."""

    def _raiser() -> None:
        raise RecoveredException("one reason", reason=OneReason())

    with testutils.raises(RecoveredException, OneReason):
        _raiser()
    # endwith


def test_raises__unexpected_exception() -> None:
    """Test for `@testutils.raises()` with unexpected exception."""

    def _raiser() -> None:
        raise AssertionError

    with pytest.raises(AssertionError), testutils.raises(RecoveredException, OneReason):
        _raiser()
    # endwith
    # endwith


def test_raises__unpexpected_reason() -> None:
    """Test `testutils.raises()` with unexpected reason."""

    def _raiser() -> None:
        raise RecoveredException("another reason", reason=AnotherReason())

    with pytest.raises(RecoveredException) as exc_info:  # noqa: SIM117
        # Test simple `with`
        with testutils.raises(RecoveredException, OneReason):
            _raiser()
        # endwith
    assert exc_info.value.get_reason().isa(AnotherReason)

    # Test merged `with`
    with (
        pytest.raises(RecoveredException) as exc_info,
        testutils.raises(RecoveredException, OneReason),
    ):
        _raiser()
    # endwith
    assert exc_info.value.get_reason().isa(AnotherReason)
