import sys
from typing import Any, Optional, TextIO


def print1(
    *values: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[TextIO] = None,
    flush: bool = False,
) -> None:
    """Pass-through to built-in print function."""
    print(*values, sep=sep, end=end, file=file, flush=flush)


def print2(
    *values: Any,
    sep: str = " ",
    end: str = "\n",
    file: Optional[TextIO] = sys.stderr,
    flush: bool = False,
) -> None:
    """Pass-through to built-in print function with stderr as default file."""
    print(*values, sep=sep, end=end, file=file, flush=flush)
