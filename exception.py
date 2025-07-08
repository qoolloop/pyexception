# Copyright (C) 2025, Kan Torii (qoolloop).
"""
Defines functionality necessary for exception handling.

Architecture is proposed in
"Practical Exception Handling" https://qoolloop.org/en-us/exception-handling

The main characteristics of the exception handling architecture are:

- Defines a `RecoveredException` that is a superclass of all recovered
  exceptions, so that the same exception handler can handle all recovered
  exceptions regardless of the cause.
- Exceptions have an `info` member that holds a `dict` of exception details,
  which can be used for showing on the UI.
"""

from __future__ import annotations

import os
import os.path
import pathlib
from typing import Any

import pylog

_logger = pylog.getLogger(__name__)


class Reason:
    """
    Super class for reasons in :class:`RecoveredException`.

    :param info: Information regarding the exception.
        The information will obtainable with :meth:`get_info()`.
    """

    def __init__(self, **info: Any) -> None:
        super().__init__()

        self._info = info

    @classmethod
    def isa(cls, other: type[Reason] | tuple[type[Reason]]) -> bool:
        """
        Check whether this reason is a subclass of another reason.

        :param other: The potential superclass(es) of this reason.

        :return: `True` if this reason is a subclass.
        """
        return issubclass(cls, other)

    def get_info(self) -> dict[str, Any]:
        """
        Get information regarding this `Reason`.

        .. note:: This doesn't return a deep copy of the `dict`, which could
          be a problem, if the caught exception is not discarded.
        """
        return self._info


# Predefined Reasons

#: Use this class itself, if reason is not specific.
UnspecificReason = Reason


# This is defined here as an example, although it actually belongs to the
# application logic layer.
class FileExists(Reason):
    """
    Raised when file or directory already exists.

    Information obtained from :meth:`Reason.get_info()` with the following keys:

    - `'path'`: c.f. :meth:`get_path()`

    :param path: Path to file or directory causing the exception.
    :param kwargs: Other information to be retrieved by :meth:`get_info()`.
    """

    def __init__(self, path: str | bytes | pathlib.Path, **kwargs: Any) -> None:
        # convert to canonical representation
        abs_path = os.fspath(os.fsdecode(os.path.abspath(path)))

        super().__init__(path=abs_path, **kwargs)

        # member variable is used so that mypy can detect errors
        # even though the information is also included in `get_info()`.
        self._path = abs_path

    def get_path(self) -> str:
        """Get path of file or directory that caused the exception."""
        return self._path


class ExceptionParent(Exception):
    """
    Superclass of all user-defined exceptions.

    This class has the features explained in
    https://qoolloop.org/en-us/exception-handling

    :param message: Message for exception
    :param reason: `Reason` for the exception. If `None`, same as
        `UnspecificReason()`.
    :param logger: Logger for logging exception.
    """

    def __init__(
        self,
        message: str,
        reason: Reason | None = None,
        logger: pylog.Logger = _logger,
    ) -> None:
        super().__init__(message)

        self._message = message
        self._reason = reason if reason else UnspecificReason()
        self._logger = logger

    def __str__(self) -> str:
        def _get_message(cause: BaseException) -> str:
            cause_message = getattr(cause, 'reason', None)  # urllib2.HTTPError
            if cause_message is None:
                # https://stackoverflow.com/a/45532289/2400328
                cause_message = getattr(cause, 'message', str(cause))

            code = getattr(cause, 'code', None)  # urllib2.HTTPError
            if code is not None:
                return f"{code}: {cause_message}"

            return str(cause_message)

        if self.__cause__ is not None:
            cause_message = _get_message(self.__cause__)
            new_message = (
                f"{self._message}, from ({type(self.__cause__)}) {cause_message}"
            )

        else:
            new_message = self._message

        return f"{self._reason}, {self._reason.get_info()}\n{new_message}"

    def get_message(self) -> str:
        """Get message assigned to this exception."""
        return self._message

    def get_reason(self) -> Reason:
        """Get the reason for this exception."""
        return self._reason

    def get_info(self) -> dict[str, Any]:
        """
        Get information regarding this exception.

        Information may build up as the exceptions are chained.

        .. note:: This doesn't return a deep copy of the `dict`, which could
          be a problem, if the caught exception is not discarded.
        """

        def _get_cause_info() -> dict[str, Any]:
            if isinstance(self.__cause__, ExceptionParent):
                cause_info = self.__cause__.get_info()

            else:
                cause_info = {}

            return cause_info

        info = _get_cause_info()
        info.update(self._reason.get_info())

        return info


class RecoveredException(ExceptionParent):
    """The superclass for exceptions that were recovered."""


# Don't need this. Should catch all exceptions in catch clause.
# class FatalException(ExceptionParent):
#     pass
