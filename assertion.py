# Copyright (C) 2025, Kan Torii (qoolloop).
"""
The modules defines different kinds of assertions.

These assertions are useful for assuring software quality and assisting
debugging.

Objectives:

- Avoid unexpected fatal situations
- Provide debug information -> logging
- Warn at non-fatal unexpected situations
- Provide means to recover from unexpected situations
- Be an alternative to documentation for preconditions and postconditions

Features:

- Assertions that raise exceptions as above
- Exception handlers that add messages/logs for debug purposes

Nomenclature:
- "Non-fatal" means there are no side effects so far within the function.
"""

from collections.abc import Generator
from contextlib import contextmanager
import logging
import threading
from typing import Any

import pylog

# FUTURE: Copy `get_function_info()` into `pyexception`
from pyqoolloop.inspection import get_function_info

from .exception import (
    ExceptionParent,
    Reason,
    RecoveredException,
)

_logger = pylog.getLogger(__name__)


class _Configuration(threading.local):
    """
    Thread local settings for this module.

    It is implemented as a stack, so that previous values can be resumed
    by popping.
    """

    def __init__(self) -> None:
        super().__init__()

        current_configuration = {
            "expect_raises": __debug__,
        }

        self._stack = [current_configuration]
        self._lock = threading.RLock()

    def set(self, key: str, value: Any) -> None:  # noqa: ANN401
        """
        Set a value for a key.

        :param key: Key of value.
        :param value: Value for key.
        """
        with self._lock:
            self._stack[-1][key] = value

    def get(self, key: str) -> Any:  # noqa: ANN401
        """
        Get a value for a key.

        :param key: Key of the value.

        :return: Value for the key.
        """
        with self._lock:
            return self._stack[-1][key]

    def push(self) -> None:
        """Create copy of the current configuration and push onto the stack."""
        with self._lock:
            self._stack.append(self._stack[-1].copy())

    def pop(self) -> None:
        """Remove the last configuration settings from the stack."""
        with self._lock:
            self._stack.pop()


_configuration = _Configuration()


@contextmanager
def localcontext(*, expect_raises: bool) -> Generator[None, None, None]:
    """
    Return context manager with a new context for the active thread.

    :param expect_raises: If `True`, `expect()` will raise on failure.
    """
    _configuration.push()

    _configuration.set('expect_raises', expect_raises)

    try:
        yield

    finally:
        _configuration.pop()

    # endtry


# Assertions


class AssertionException(AssertionError, ExceptionParent):
    """
    Replacement for :class:`AssertionError` with info.

    :param message: Message to be logged if `condition` is `False`.
    :param info: Information regarding the exception.
    """

    def __init__(self, message: str, info: dict[str, Any] | None = None) -> None:
        AssertionError.__init__(self, message)

        info = info if info else {}
        ExceptionParent.__init__(
            self, message, reason=AssertionException.Assertion(**info)
        )

    class Assertion(Reason):
        """`Reason` for assertion."""


def imperative(
    condition: bool,  # noqa: FBT001
    message: str | None = None,
    *,
    info: dict[str, Any] | None = None,
    level: pylog.Level = pylog.Level.ERROR,
    logger: logging.Logger = _logger,
) -> None:
    """
    Raise exception, if condition is not met.

    :param condition: Needs to be `True` not to raise an exception.
    :param message: Message to be logged if `condition` is `False`.
    :param info: Information regarding the exception.
    :param level: Level for logging.
    :param logger: Logger to use for logging.

    :raise AssertionError: `condition` is not met.

    .. note:: Add to `extend-allowed-calls` to avoid ruff `FBT003` warning.
      https://docs.astral.sh/ruff/settings/#lint_flake8-boolean-trap_extend-allowed-calls
    """
    if not condition:
        if message is None:
            _, function_name, _ = get_function_info(2)
            message = "Imperative failure in " + function_name

        logger.log(level.value, message)
        raise AssertionException(message, info)

    # endif


def expect(  # noqa: PLR0913
    condition: bool,  # noqa: FBT001 Same as `assert`
    message: str | None = None,
    *,
    info: dict[str, Any] | None = None,
    level: pylog.Level = pylog.Level.WARNING,
    logger: pylog.Logger = _logger,
    throw: bool | None = None,
) -> None:
    """
    Log warning, if condition is not met.

    :param condition: Condition to check.
    :param message: Message to log, when `condition` is not met.
    :param info: Information regarding the exception, if thrown.
    :param level: Level for logging.
    :param logger: Logger to use for logging.
    :param throw: Whether to raise an exception when `not condition`.
      If `None`, will respect configuration setting.

    :raise AssertionError: `condition` is not met,
      and (`throw` is True or (`throw` is None and configuration set to raise))

    Can be configured to raise exception, if condition is not met.
    Can be configured to be disabled.

    Configuration is set in the `_configuration` variable.

    .. note:: Add to `extend-allowed-calls` to avoid ruff `FBT003` warning.
      https://docs.astral.sh/ruff/settings/#lint_flake8-boolean-trap_extend-allowed-calls
    """
    if not condition:
        if message is None:
            _, function_name, _ = get_function_info(2)
            message = "Expect failure in " + function_name

        logger.log(level.value, message)

        if throw or ((throw is None) and _configuration.get('expect_raises')):
            raise AssertionException(message, info)

    # endif


# Section handlers


@contextmanager
def _exception_converter(
    reason: Reason,
    # FUTURE: `force_reason` argument to enable/disable overwriting reason
    raise_message: str,
    pass_through: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    logger: pylog.Logger = _logger,
) -> Generator[None, None, None]:
    """
    Context manager for converting raised exceptions to `RecoveredException`.

    :param reason: `Reason` to set to the new exception.
    :param raise_message: Message to log, when exception is converted.
    :param pass_through: `None` or (`tuple` of exceptions that shouldn't be
      converted.
    :param logger: logger to use for logging exceptions.

    :raise RecoveredException: Exception occurred within the suite.
    :raise Exception: Exceptions that are specified in `pass_through` are
      reraised as is.
    """
    try:
        yield

    except BaseException as exception:
        if not isinstance(pass_through, tuple):
            if pass_through is None:
                pass_through = ()

            else:
                pass_through = (pass_through,)

        if isinstance(exception, pass_through):
            raise

        if logger:
            logger.exception(raise_message)

        raise RecoveredException(
            raise_message, reason=reason, logger=logger
        ) from exception

    # endtry


class RecoveredReason(Reason):
    """Reason raised by :func:`recoverable()` when an exception is raised."""


@contextmanager
def recoverable(
    pass_through: type[Exception] | tuple[type[Exception], ...] | None = None,
    logger: pylog.Logger = _logger,
) -> Generator[None, None, None]:
    """
    Context manager for converting raised exceptions to `RecoveredException`.

    :param pass_through: `None` or (`tuple` of exceptions that shouldn't be
      converted to `RecoveredException`.
    :param logger: logger to use for logging exceptions.

    :raise RecoveredException: Exception occurred within the suite.
    :raise Exception: Exceptions that are specified in `pass_through` are
      reraised as is.
    """
    with _exception_converter(
        reason=RecoveredReason(),
        raise_message="Exception caught in `recoverable()`",
        pass_through=pass_through,
        logger=logger,
    ):
        yield

    # endwith


class ViolatedPreconditionReason(RecoveredReason):
    """Reason raised by :func:`precondition()` when precondition is not satisfied."""


@contextmanager
def precondition(logger: pylog.Logger = _logger) -> Generator[None, None, None]:
    """
    Specify section where preconditions are listed.

    A precondition section includes :func:`imperative()` and :func:`expect()`.

    Log includes "Violated precondition" when exception is raised.

    :param logger: Logger to use for logging exceptions.

    :raise RecoveredException: At least one precondition is not met.
    """
    with _exception_converter(
        reason=ViolatedPreconditionReason(),
        raise_message="Violated precondition",
        logger=logger,
    ):
        yield

    # endwith


@contextmanager
def postcondition() -> Generator[None, None, None]:
    # FUTURE: `recover` argument to convert to `RecoveredException`
    """
    Specify section where postconditions are listed.

    A postcondition section includes :func:`imperative()` and :func:`expect()`.

    :raise AssertionException: Postcondition is not met.
    """
    yield


@contextmanager
def nonfatal_section(
    pass_through: type[Exception] | tuple[type[Exception], ...] | None = None,
    logger: pylog.Logger = _logger,
) -> Generator[None, None, None]:
    """
    Specify section where exceptions are non-fatal.

    :raise RecoveredException: Exception is raised.
    """
    with recoverable(pass_through=pass_through, logger=logger):
        yield

    # endwith


@contextmanager
def fatal_section() -> Generator[None, None, None]:
    """
    Specify section where exceptions are fatal.

    :raise Exception: Relayed exception that was raised in the section.
    """
    yield
