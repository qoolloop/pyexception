# Copyright (C) 2025, Kan Torii (qoolloop).
"""Tests for the `exception` module."""

from collections.abc import Iterable
import http.client
import os
import pathlib
from typing import Any
import urllib.error

import pytest

from .exception import (
    ExceptionParent,
    FileExists,
    Reason,
    RecoveredException,
)

# FileExists


# FUTURE: Test on Windows
@pytest.mark.parametrize(
    'path, expected_path',
    (
        ('', os.getcwd()),
        ('材料', os.path.join(os.getcwd(), '材料')),
        ('\x00path', os.path.join(os.getcwd(), '\x00path')),
        ('\xc2', os.path.join(os.getcwd(), 'Â')),
        # https://jod.al/2019/12/10/pathlib-and-paths-with-arbitrary-bytes/
        (b'\xc2', os.path.join(os.getcwd(), '\udcc2')),
        ('/', '/'),
        ('/材料', '/材料'),
        ('/\x00材料', '/\x00材料'),
        ('/\xc3', '/Ã'),
        # https://jod.al/2019/12/10/pathlib-and-paths-with-arbitrary-bytes/
        (b'/\xc3', '/\udcc3'),
    ),
)
def test__FileExists__path(path: str | bytes, expected_path: str) -> None:
    """Test path information for `FileExists`."""
    path_list: Iterable[str | bytes | pathlib.Path] = (
        path,
        os.fsencode(path),
        pathlib.Path(os.fsdecode(path)),
    )
    for each in path_list:
        reason = FileExists(path=each)

        assert expected_path == reason.get_path()

        info = reason.get_info()
        assert expected_path == info['path']

    # endfor


# RecoveredException


@pytest.mark.parametrize(
    "cause_message, cause_exception_type",
    (
        ("Cause Message", RecoveredException),
        ("Standard exception cause message", AssertionError),
    ),
)
def test__RecoveredException__cause(
    cause_message: str, cause_exception_type: type[Exception]
) -> None:
    """Test message string of `RecoveredException` caused by another exception."""
    cause = cause_exception_type(cause_message)

    new_exception_message = "New Exception"

    with pytest.raises(RecoveredException) as exc_info:
        raise RecoveredException(
            new_exception_message,
        ) from cause

    new_exception = exc_info.value
    assert new_exception_message in str(new_exception)
    assert cause_message in str(new_exception)


def test__RecoveredException__HTTPError_cause() -> None:
    """Test message string of `RecoveredException` caused by `HTTPError`."""
    cause_message = "Not Found"
    cause = urllib.error.HTTPError(
        url="http://example.com",
        code=404,
        msg=cause_message,
        hdrs=http.client.HTTPMessage(),
        fp=None,
    )

    new_exception_message = "New Exception Message"

    with pytest.raises(RecoveredException) as exc_info:
        raise RecoveredException(
            new_exception_message,
        ) from cause

    new_exception = exc_info.value
    assert new_exception_message in str(new_exception)
    assert cause_message in str(new_exception)


def test__ExceptionParent__str() -> None:
    """Test message string of `ExceptionParent`."""

    class _NewReason(Reason):
        pass

    class _NewException(ExceptionParent):
        pass

    class _CauseException(Exception):
        pass

    cause_message = "A Cause Message"
    cause = _CauseException(cause_message)

    message = "A Message"
    with pytest.raises(_NewException) as exc_info:
        raise _NewException(message, reason=_NewReason(key='value')) from cause

    exception = exc_info.value
    assert message in str(exception)
    assert cause_message in str(exception)
    assert "_NewReason" in str(exception)
    assert "key" in str(exception)
    assert "value" in str(exception)


def test__ExceptionParent__default_info() -> None:
    """Make sure that `{}` is not used as the default argument for `ExceptionParent`."""
    one_exception = ExceptionParent("message")
    info = one_exception.get_info()
    assert len(info) == 0

    info["key"] = "value"

    another_exception = ExceptionParent("another message")
    assert len(another_exception.get_info()) == 0, (
        "This will fail if `{}` is used as default for `info`"
    )


def test__ExceptionParent__chained_info() -> None:
    """Make sure exception information accumulates when reraised."""

    class _CauseReason(Reason):
        pass

    class _ReraisedReason(Reason):
        pass

    # `raise` is reserved
    cause_info = {"cause": True}
    additional_info = {"raise": "Yes"}
    combined_info: dict[str, Any] = {"cause": True, "raise": "Yes"}

    with pytest.raises(ExceptionParent) as exc_info:
        try:
            raise ExceptionParent("message", reason=_CauseReason(**cause_info))  # noqa: TRY301

        except Exception as interim_exception:
            raise RecoveredException(
                "raised", reason=_ReraisedReason(**additional_info)
            ) from interim_exception

    caught_exception = exc_info.value
    assert caught_exception.get_info() == combined_info
