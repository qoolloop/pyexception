# Copyright (C) 2025, Kan Torii (qoolloop).
"""Module with useful functions for unit testing."""

from __future__ import annotations

from collections.abc import Iterable
from types import TracebackType

from typing_extensions import Self

from .exception import (
    ExceptionParent,
    Reason,
)


class raises:  # noqa: N801
    """Context handler that expects exceptions to be raised in the suite."""

    def __init__(
        self,
        exception: type[ExceptionParent],
        reason: type[Reason],
        info_keys: Iterable[str] = (),
    ) -> None:
        """
        Initialize context manager.

        :param exception: Type of exception that is expected
        :param reason: The expected reason for the raised exception.
        :param info_keys: Keys that are expected in the information of the
          raised exception.
        """
        self.__exception = exception
        self.__reason_type = reason

        if isinstance(info_keys, (list, tuple)):
            self.__info_keys = info_keys

        else:
            self.__info_keys = (info_keys,)
        # endif

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        assert exception_value is not None, (
            f"Didn't raise exception: {self.__exception.__class__.__name__}"  # type: ignore[reportUnknownMemberType,unused-ignore]
        )
        assert (exception_type is not None) and (traceback is not None), (  # noqa: PT018
            "Inconsistent arguments"
        )  # for mypy

        if not issubclass(exception_type, self.__exception):
            return False

        assert isinstance(exception_value, self.__exception)  # for mypy
        if not exception_value.get_reason().isa(self.__reason_type):
            return False

        info = exception_value.get_info()
        for each in self.__info_keys:
            assert each in info, f"{each} not in {info}"

        return True
