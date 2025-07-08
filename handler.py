# Copyright (C) 2025, Kan Torii (qoolloop).
"""Useful context managers for use with the `with` statement."""

from __future__ import annotations

from contextlib import AbstractContextManager
import logging
from types import TracebackType
from typing import (
    Callable,
    Optional,
)

from typing_extensions import Self


# Context managers are not capitalized
# c.f. https://docs.python.org/3/library/contextlib.html
class exception_handler(  # noqa: N801
    AbstractContextManager['exception_handler']
):
    """
    Context manager for exception handling.

    To be used in a with statement to:

    - handle exceptions with a common handler
    - ignore some exceptions
    - log exceptions to a specific logger
    """

    HandlerType = Callable[[Optional[BaseException], Optional[TracebackType]], bool]

    @staticmethod
    def _empty_handler(
        exception: BaseException | None,  # noqa: ARG004
        traceback: TracebackType | None,  # noqa: ARG004
    ) -> bool:
        # ExceptionParent has logger
        return False

    def __init__(
        self,
        *,
        handler: HandlerType | None = None,
        ignore: None | type[BaseException] | tuple[type[BaseException], ...] = None,
        logger: logging.Logger | None = None,
        handle_base_exception: bool = False,
    ) -> None:
        """
        Initialize exception handler.

        :param handler: function to handle exceptions with the following
          signature (return `True` to suppress exception)::
            def function(
              exception: Optional[BaseException],
              traceback: Optional[TracebackType]
            ) -> bool
          If `None`, nothing will be done in the handler.
        :param ignore: `None`, or exceptions to ignore. Ignored
          exceptions will not be handled with `handler`.
        :param logger: logger to log exceptions. `None` to not log.
        :param handle_base_exception: If `False`, `handler` will not be called
          for subclasses of `BaseException` that are not subclasses of
          `Exception`.
        """
        if handler is None:
            # Couldn't specify `_empty_handler.__func__` for default parameter
            # with `mpypy`
            handler = exception_handler._empty_handler

        assert (handler != exception_handler._empty_handler) or (
            ignore not in (None, ())
        ), "You probably didn't mean to do this"

        if not isinstance(ignore, tuple):
            if ignore is None:
                ignore = ()

            else:
                ignore = (ignore,)

        self.__ignored_exceptions = ignore
        self.__handler = handler
        self.__logger = logger
        self.__handle_base_exception = handle_base_exception

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        # Type hints taken from https://stackoverflow.com/q/49959656

        if exception_value is not None:
            assert exception_type is not None

            if self.__logger:
                self.__logger.exception("Exception caught")

            if isinstance(exception_value, self.__ignored_exceptions):
                return True

            if (not self.__handle_base_exception) and not issubclass(
                exception_type, Exception
            ):
                return False

            suppress_exception = self.__handler(exception_value, traceback)
            return suppress_exception

        return False


class ignore_exception(exception_handler):  # noqa: N801
    """Context manager that ignores specific exceptions."""

    def __init__(
        self,
        ignore: tuple[type[Exception], ...],
        *,
        handler: exception_handler.HandlerType | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize context manager.

        :param handler: function to handle exceptions with the following
          signature (return `True` to suppress exception)::
            def function(
              exception: Optional[BaseException],
              traceback: Optional[TracebackType]
            ) -> bool
          If `None`, nothing will be done in the handler.
        :param ignore: Tuple of exceptions to ignore. Ignored
          exceptions will not be handled with `handler`.
        :param logger: logger to log exceptions. `None` to not log.
        """
        super().__init__(handler=handler, ignore=ignore, logger=logger)


class log_exception(exception_handler):  # noqa: N801
    """Context manager to log exception raised."""

    def __init__(
        self,
        logger: logging.Logger | None,
        *,
        handler: exception_handler.HandlerType | None = None,
        ignore: tuple[type[Exception], ...] | None = None,
    ) -> None:
        """
        Initialize exception handler.

        :param logger: logger to log exceptions. `None` to not log.
        :param handler: function to handle exceptions with the following
          signature (return `True` to suppress exception)::
            def function(
              exception: Optional[BaseException],
              traceback: Optional[TracebackType]
            ) -> bool
          If `None`, nothing will be done in the handler.
        :param ignore: `None`, or tuple of exceptions to ignore. Ignored
          exceptions will not be handled with `handler`.
        """
        super().__init__(handler=handler, ignore=ignore, logger=logger)
