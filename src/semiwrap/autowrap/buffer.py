import io
import contextlib
import inspect


class RenderBuffer:
    def __init__(self) -> None:
        self._buffer = io.StringIO()

        self._indent = ""
        self._indentlen = 0

    def getvalue(self) -> str:
        return self._buffer.getvalue()

    def rel_indent(self, spaces: int):
        self._indentlen += spaces
        self._indent = " " * self._indentlen

    @contextlib.contextmanager
    def indent(self, spaces: int = 2):
        self._indentlen += spaces
        self._indent = " " * self._indentlen
        try:
            yield
        finally:
            self._indentlen -= spaces
            self._indent = " " * self._indentlen

    def writeln(self, s: str = ""):
        if not s:
            self._buffer.write("\n")
        else:
            for line in s.splitlines(False):
                if line:
                    self._buffer.write(f"{self._indent}{line}\n")
                else:
                    self._buffer.write("\n")

    def write_trim(self, s: str):
        for line in inspect.cleandoc(s).splitlines(False):
            if line:
                self._buffer.write(f"{self._indent}{line}\n")
            else:
                self._buffer.write("\n")
