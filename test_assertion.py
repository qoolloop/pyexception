# Copyright (C) 2025, Kan Torii (qoolloop).
"""Tests for the `assertion` module."""

from functools import partial
import logging
from typing import (
    Any,
    Callable,
    Protocol,
)

import pylog

# FUTURE: These are causing a cyclical dependency with pyqoolloop. Include \
# pyexception in pyqoolloop.
from pyqoolloop.inspection import get_function_info
from pyqoolloop.testutils import (
    combine_lists,
    included,
)
import pytest

from .assertion import (
    AssertionException,
    expect,
    fatal_section,
    imperative,
    localcontext,
    nonfatal_section,
    postcondition,
    precondition,
    recoverable,
)
from .exception import (
    RecoveredException,
)

_logger = pylog.getLogger(__name__)


_ASSERTIONS_ARGUMENTS = 'function, message_title'

_ASSERTIONS: list[list[Any]] = [
    [imperative, "Imperative"],
    [partial(expect, throw=True), "Expect"],
]

_parametrize__assertions = pytest.mark.parametrize(_ASSERTIONS_ARGUMENTS, _ASSERTIONS)

_LOG_LEVELS_ARGUMENTS = 'level, pylog_level'
_LOG_LEVELS: list[list[Any]] = [
    [logging.ERROR, pylog.ERROR],
    [logging.WARNING, pylog.WARNING],
]

_parametrize__log_levels = pytest.mark.parametrize(_LOG_LEVELS_ARGUMENTS, _LOG_LEVELS)


_parametrize__assertions__log_levels = pytest.mark.parametrize(
    _ASSERTIONS_ARGUMENTS + ', ' + _LOG_LEVELS_ARGUMENTS,
    combine_lists(_ASSERTIONS, _LOG_LEVELS),
)


@_parametrize__assertions
def test__assertions(
    function: Callable[[bool], None],
    message_title: str,  # noqa: ARG001
) -> None:
    """Test `imperative()`."""
    function(True)

    with pytest.raises(AssertionError):
        function(False)

    # endwith


def test__expect__throw() -> None:
    """Test that `expect()` raises exception depending on `throw` argument."""
    expect(True)
    expect(False, throw=False)  # `expect()` can raise based on configuration

    expect(True, throw=True)

    with pytest.raises(AssertionError):
        expect(False, throw=True)

    # endwith


@_parametrize__assertions
def test__assertions__default_message(
    function: Callable[[bool], None], message_title: str
) -> None:
    """Test default message of exception raised by assertions."""
    _, test_function_name, _ = get_function_info(1)

    with pytest.raises(AssertionError) as exc_info:
        function(False)

    exception = exc_info.value
    assert message_title in str(exception)
    assert test_function_name in str(exception)


@_parametrize__assertions
def test__assertions__message(
    function: Callable[[bool, str], None],
    message_title: str,  # noqa: ARG001
) -> None:
    """Test message of `AssertionException` raised by assertions."""
    message = "a message"

    with pytest.raises(AssertionError) as exc_info:
        function(False, message)

    exception = exc_info.value
    assert message in str(exception)


class _AssertionFunctionWithMessageInfo(Protocol):
    """Function for assertions with `message` and `info` argument."""

    def __call__(
        self,
        condition: bool,  # noqa: FBT001
        message: str,
        info: dict[str, Any],
    ) -> None: ...


@_parametrize__assertions
def test__assertions__message_info(
    function: _AssertionFunctionWithMessageInfo,
    message_title: str,  # noqa: ARG001
) -> None:
    """Test `message` and `info` of `AssertionException` raised by assertions."""
    message = "a message"
    info: dict[str, Any] = {'a': 1, 'bcd': "bcd"}

    with pytest.raises(AssertionException) as exc_info:
        function(False, message, info=info)

    exception = exc_info.value
    assert isinstance(exception, AssertionError)
    assert message in str(exception)
    assert included(info, exception.get_info())


class _AssertionFunctionWithInfo(Protocol):
    """Function for assertions with `info` argument."""

    def __call__(
        self,
        condition: bool,  # noqa: FBT001
        info: dict[str, Any],
    ) -> None: ...


@_parametrize__assertions
def test__assertions__info(
    function: _AssertionFunctionWithInfo,
    message_title: str,  # noqa: ARG001
) -> None:
    """Test `info` of `AssertionException` raised by assertions."""
    info: dict[str, Any] = {'a': 1, 'bcd': "str value"}

    with pytest.raises(AssertionException) as exc_info:
        function(False, info=info)

    exception = exc_info.value
    assert isinstance(exception, AssertionError)
    assert 'a' in str(exception)
    assert '1' in str(exception)
    assert 'bcd' in str(exception)
    assert 'str value' in str(exception)
    assert included(info, exception.get_info())


class _Logger(pylog.Logger):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        # self.level: int already exists
        self.level_: int | None = None
        self.msg_: str | None = None

    def log(  # type: ignore[override]
        self, level: int, msg: str, *args: Any, **kwargs: Any
    ) -> None:
        super().log(level, msg, *args, **kwargs)

        self.level_ = level
        self.msg_ = msg

    def exception(  # type: ignore[override]
        self, msg: str, *args: Any, **kwargs: Any
    ) -> None:
        self.log(pylog.ERROR, msg, *args, **kwargs)


class _AssertionFunction(Protocol):
    """Function for assertions."""

    def __call__(
        self,
        condition: bool,  # noqa: FBT001
        message: str,
        info: dict[str, Any],
        level: pylog.Level,
        logger: pylog.Logger,
    ) -> None: ...


@_parametrize__assertions__log_levels
def test__assertions__logger(
    function: _AssertionFunction,
    message_title: str,  # noqa: ARG001
    level: int,
    pylog_level: pylog.Level,
) -> None:
    """Test log for assertions."""
    message = "a message"
    info: dict[str, Any] = {'a': 1, 'bcd': "bcd"}
    logger = _Logger('test__imperative__logger')

    with pytest.raises(AssertionException) as exc_info:
        function(False, message, info=info, level=pylog_level, logger=logger)

    exception = exc_info.value
    assert isinstance(exception, AssertionError)
    assert str.find(logger.msg_, message) >= 0  # type: ignore[arg-type]
    assert logger.level_ == level


@_parametrize__assertions__log_levels
def test__assertions__logger__none(
    function: _AssertionFunction,
    message_title: str,  # noqa: ARG001
    level: int,  # noqa: ARG001
    pylog_level: pylog.Level,
) -> None:
    """Test log for no failure with `expect()`."""
    message = "a message"
    info: dict[str, Any] = {'a': 1, 'bcd': "bcd"}
    logger = _Logger('test__imperative__logger')

    function(True, message, info=info, level=pylog_level, logger=logger)
    assert logger.msg_ is None
    assert logger.level_ is None


@_parametrize__log_levels
def test__expect__logger(level: int, pylog_level: pylog.Level) -> None:
    """Test log for `expect()`."""
    message = "a message"
    info: dict[str, Any] = {'a': 1, 'bcd': "bcd"}
    logger = _Logger('test__imperative__logger')

    expect(False, message, info=info, level=pylog_level, logger=logger, throw=False)
    assert str.find(logger.msg_, message) >= 0  # type: ignore[arg-type]
    assert logger.level_ == level


def test__expect__throw_with_configuration() -> None:
    """Test `expect_raises` for `_configuration`."""
    with localcontext(expect_raises=False):
        expect(False)

    with localcontext(expect_raises=True), pytest.raises(AssertionError):
        expect(False)

        # endwith

    # endwith


@pytest.mark.parametrize(
    'pass_through, passed_exception, caught_exception',
    (
        (None, None, AssertionError),
        (AssertionError, AssertionError, ArithmeticError),
        (RecoveredException, RecoveredException, EOFError),
        # `KeyboardInterrupt` prints confusing log.
        # ((KeyError,), KeyError, KeyboardInterrupt),  # noqa: ERA001
        ((KeyError,), KeyError, MemoryError),
        ((GeneratorExit, ImportError), ImportError, IndexError),
    ),
)
def test__recoverable__pass_through(
    pass_through: type[Exception] | tuple[type[Exception], ...] | None,
    passed_exception: type[Exception],
    caught_exception: type[Exception],
) -> None:
    """Test `pass_through` argument of `recoverable()`."""
    logger = _Logger(__name__)

    with recoverable(pass_through=pass_through, logger=logger):
        pass

    assert logger.msg_ is None

    if passed_exception:
        with (
            pytest.raises(passed_exception),
            recoverable(pass_through=pass_through, logger=logger),
        ):
            raise passed_exception()

    with (
        pytest.raises(RecoveredException),
        recoverable(pass_through=pass_through, logger=logger),
    ):
        raise caught_exception()

    # endwith


def test__precondition() -> None:
    """Test with no exception in `precondition()`."""
    with precondition():
        pass

    # endwith


def test__precondition__raise() -> None:
    """Test that exception in `precondition()` raises `RecoveredException`."""
    with pytest.raises(RecoveredException), precondition():
        imperative(False)

    # endwith


def test__precondition__log() -> None:
    """Test log of `precondition()`."""
    expected_message = "Violated precondition"

    logger = _Logger(__name__)

    with precondition(logger=logger):
        imperative(True)

    assert logger.msg_ is None

    with pytest.raises(RecoveredException), precondition(logger=logger):
        imperative(False)

    assert str.find(logger.msg_, expected_message) >= 0  # type: ignore[arg-type]


def test__postcondition() -> None:
    """Test `postcondition()` with no exception."""
    with postcondition():
        pass

    # endwith


def test__postcondition__raise() -> None:
    """Test that exception in `postcondition()` raises `AssertionException`."""
    with pytest.raises(AssertionException), postcondition():
        imperative(False)

    # endwith


def test__nonfatal_section() -> None:
    """Test `nonfatal_section()` with no exception."""
    with nonfatal_section():
        pass

    # endwith


def test__nonfatal_section__raise() -> None:
    """Test that assertion in `nonfatal_section()` raises `RecoveredException`."""
    with pytest.raises(RecoveredException), nonfatal_section():
        imperative(False)

    # endwith


def test__fatal_section() -> None:
    """Test `fatal_section()` with no exception."""
    with fatal_section():
        pass

    # endwith


@pytest.mark.parametrize('raise_exception', (OSError,))
def test__fatal_section__raise(raise_exception: type[Exception]) -> None:
    """Test that `fatal_section()` passes through raised exceptions."""
    with pytest.raises(raise_exception), fatal_section():
        raise raise_exception()

    # endwith
