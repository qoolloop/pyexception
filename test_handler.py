# Copyright (C) 2025, Kan Torii (qoolloop).
"""Tests for the `handler` module."""

from logging import Logger
from types import TracebackType
from typing import (
    Any,
    Callable,
    Optional,
)

import pylog

# FUTURE: This is causing a cyclical dependency with pyqoolloop.
# Include pyexception in pyqoolloop
from pyqoolloop.testutils import combine_lists
import pytest

from .handler import (
    exception_handler,
    ignore_exception,
    log_exception,
)

_logger = pylog.getLogger(__name__)


# FUTURE: Move to pyqoolloop
def _partial_class(
    base_cls: type, /, *partial_args: Any, **partial_kwargs: Any
) -> type:
    """
    Return subclass with `__init__()` partially applied.

    This is useful for creating a class with some arguments already set,
    so that the class can be instantiated with fewer arguments later.

    :param base_cls: The base class to extend.
    :param partial_args: Positional arguments for `__init__()` of `base_cls`.
    :param partial_kwargs: Keyword arguments to partially apply.
    :return: A new class that extends `base_cls` with a modified `__init__()`.
    """

    class PartialClass(base_cls):  # type: ignore[reportUntypedBaseClass,unused-ignore,misc]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*partial_args, *args, **partial_kwargs, **kwargs)  # type: ignore[reportUnknownMemberType,unused-ignore]

    PartialClass.__name__ = f"Partial{base_cls.__name__}"
    return PartialClass


class AnException(Exception):
    """An example of an exception."""


def test_exception_handler__raise() -> None:
    """Test that handler for `exception_handler()` raises the caught exception."""
    counter = {
        'count': 0,
    }

    def _handler(
        exception: Optional[BaseException],  # noqa: ARG001
        traceback: Optional[TracebackType],  # noqa: ARG001
    ) -> bool:
        counter['count'] += 1
        return False

    with pytest.raises(AnException), exception_handler(handler=_handler):
        raise AnException("just raise it")
        # endwith

    assert counter['count'] == 1


def test_exception_handler__handler() -> None:
    """Test that `exception_handler()` doesn't raise the caught exception."""
    counter = {
        'count': 0,
    }

    def _handler(
        exception: Optional[BaseException],  # noqa: ARG001
        traceback: Optional[TracebackType],  # noqa: ARG001
    ) -> bool:
        counter['count'] += 1
        return True

    with exception_handler(handler=_handler):
        pass

    assert counter['count'] == 0

    with exception_handler(handler=_handler):
        raise AnException("just raise it")

    assert counter['count'] == 1


def _parametrize__exception_handlers(
    *exc_handlers: type[exception_handler],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return pytest.mark.parametrize(
        "raise_this, ignore_these, handler_to_test",
        combine_lists(
            [
                [AnException, AnException],
                [AnException, (AnException,)],
                [AnException, (AnException, RuntimeError)],
                [RuntimeError, (AnException, RuntimeError)],
            ],
            list(exc_handlers),
        ),
    )


def _test_exception_handler_call(
    raise_this: type[Exception],
    ignore_these: type[Exception] | tuple[type[Exception], ...],
    handler_to_test: type[exception_handler],
    *,
    handler_called: bool,
) -> None:
    counter = {
        'count': 0,
    }

    def _handler(
        exception: Optional[BaseException],  # noqa: ARG001
        traceback: Optional[TracebackType],  # noqa: ARG001
    ) -> bool:
        counter['count'] += 1
        return False

    with handler_to_test(handler=_handler, ignore=ignore_these, logger=_logger):
        raise raise_this("just raise it")

    assert (counter['count'] > 0) is handler_called


@_parametrize__exception_handlers(exception_handler, log_exception, ignore_exception)
def test_exception_handler__handler_with_ignore(
    raise_this: type[Exception],
    ignore_these: type[Exception] | tuple[type[Exception], ...],
    handler_to_test: type[exception_handler],
) -> None:
    """Test handlers are not called for exception handlers if exceptions are ignored."""
    _test_exception_handler_call(
        raise_this, ignore_these, handler_to_test, handler_called=False
    )


@_parametrize__exception_handlers(exception_handler, log_exception, ignore_exception)
def test_exception_handler__ignore(
    raise_this: type[Exception],
    ignore_these: type[Exception] | tuple[type[Exception], ...],
    handler_to_test: type[exception_handler],
) -> None:
    """Test exception handlers with exceptions to ignore."""
    with handler_to_test(ignore=ignore_these, logger=None):
        raise raise_this("just raise it")
    # endwith


def _default_handler(
    exception: Optional[BaseException],  # noqa: ARG001
    traceback: Optional[TracebackType],  # noqa: ARG001
) -> bool:
    # ExceptionParent has logger
    return False


def test_exception_handler__nothing() -> None:
    """Test `exception_handler()` without ignoring any exceptions."""
    with pytest.raises(AnException), exception_handler(handler=_default_handler):
        raise AnException("just raise it")
        # endwith


def test_exception_handler__pass() -> None:
    """Test `exception_handler()` around `pass`."""
    with exception_handler(handler=_default_handler):
        pass
    # endwith


@_parametrize__exception_handlers(exception_handler, log_exception, ignore_exception)
def test_exception_handler__log(
    raise_this: type[Exception],  # noqa: ARG001
    ignore_these: type[Exception] | tuple[type[Exception], ...],  # noqa: ARG001
    handler_to_test: type[exception_handler],
) -> None:
    """Test logging of exception handlers."""

    class _Logger(Logger):
        def __init__(self) -> None:
            super().__init__("name")
            self.message: Optional[str] = None

        def exception(  # type:ignore[override]
            self,
            message: str,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            super().exception(message, *args, **kwargs)
            self.message = message

        # enddef

    logger = _Logger()

    with handler_to_test(handler=_default_handler, logger=logger, ignore=None):
        pass

    assert logger.message is None

    with (
        pytest.raises(AssertionError),
        handler_to_test(handler=_default_handler, logger=logger, ignore=None),
    ):
        raise AssertionError

    # endwith

    assert logger.message is not None


@_parametrize__exception_handlers(exception_handler, log_exception, ignore_exception)
def test_exception_handler__default_handler(
    raise_this: type[Exception],  # noqa: ARG001
    ignore_these: type[Exception] | tuple[type[Exception], ...],
    handler_to_test: type[exception_handler],
) -> None:
    """Test exception handlers with their default handlers."""

    class _Logger(Logger):
        def __init__(self) -> None:
            super().__init__("name")
            self.message: Optional[str] = None

        def exception(  # type:ignore[override]
            self,
            message: str,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            super().exception(message, *args, **kwargs)
            self.message = message

        # enddef

    logger = _Logger()

    with handler_to_test(ignore=ignore_these, logger=logger):
        pass

    assert logger.message is None

    with (
        pytest.raises(AssertionError),
        handler_to_test(ignore=ignore_these, logger=logger),
    ):
        raise AssertionError

    # endwith

    assert logger.message is not None


@pytest.mark.parametrize(
    "raise_this, ignore_these, handle_base_exception, handler_called, handler_to_test",
    combine_lists(
        [
            [SystemExit, None, False, False],
            [SystemExit, None, True, True],
            [SystemExit, AnException, False, False],
            [SystemExit, (AnException,), False, False],
            [SystemExit, (AnException, RuntimeError), False, False],
            [SystemExit, (AnException, RuntimeError), False, False],
            [SystemExit, AnException, True, True],
            [SystemExit, (AnException,), True, True],
            [SystemExit, (AnException, RuntimeError), True, True],
            [SystemExit, (AnException, RuntimeError), True, True],
        ],
        exception_handler,
    ),
)
def test_exception_handler__BaseException(
    raise_this: type[Exception],
    ignore_these: type[Exception] | tuple[type[Exception], ...],
    handle_base_exception: bool,  # noqa: FBT001
    handler_called: bool,  # noqa: FBT001
    handler_to_test: type[exception_handler],
) -> None:
    """Test exception handlers with `handle_base_exception` argument."""
    handler = _partial_class(
        handler_to_test, handle_base_exception=handle_base_exception
    )

    with pytest.raises(raise_this):
        _test_exception_handler_call(
            raise_this, ignore_these, handler, handler_called=handler_called
        )

    # endwith


@pytest.mark.parametrize(
    "raise_this, ignore_these, handle_base_exception, handler_to_test",
    combine_lists(
        [
            [AnException, AnException, True],
            [AnException, (AnException,), True],
            [AnException, (AnException, RuntimeError), True],
            [RuntimeError, (AnException, RuntimeError), True],
            [AnException, AnException, True],
            [AnException, (AnException,), True],
            [AnException, (AnException, RuntimeError), True],
            [RuntimeError, (AnException, RuntimeError), True],
            [SystemExit, SystemExit, False],
            [SystemExit, (SystemExit,), False],
            [SystemExit, (SystemExit, RuntimeError), False],
            [SystemExit, (SystemExit, RuntimeError), False],
            [SystemExit, SystemExit, False],
            [SystemExit, (SystemExit,), False],
            [SystemExit, (SystemExit, RuntimeError), False],
            [SystemExit, (SystemExit, RuntimeError), False],
        ],
        exception_handler,
    ),
)
def test_exception_handler__BaseException__ignore(
    raise_this: type[Exception],
    ignore_these: type[Exception] | tuple[type[Exception], ...],
    handle_base_exception: bool,  # noqa: FBT001
    handler_to_test: type[exception_handler],
) -> None:
    """Test exception handlers with `handle_base_exception` argument."""
    exc_handler = _partial_class(
        handler_to_test, handle_base_exception=handle_base_exception
    )

    _test_exception_handler_call(
        raise_this, ignore_these, exc_handler, handler_called=False
    )

    # endwith
