import io
import re
import sys
import typing

from ._pcpp import Preprocessor, OutputDirective, Action


class PreprocessorError(Exception):
    pass


class CustomPreprocessor(Preprocessor):
    def __init__(self):
        Preprocessor.__init__(self)
        self.errors = []

        # This removes the contents of all include files from the output
        self.passthru_includes = re.compile(r".*")

    def on_error(self, file, line, msg):
        self.errors.append("%s:%d error: %s" % (file, line, msg))

    def on_include_not_found(
        self, is_malformed, is_system_include, curdir, includepath
    ):
        raise OutputDirective(Action.IgnoreAndPassThrough)

    def on_comment(self, tok):
        return True


def preprocess_file(
    fname: str, include_paths: typing.List[str] = [], defines: typing.List[str] = []
) -> str:
    """
    Preprocesses the file via pcpp. Useful for dealing with files that have
    complex macros in them, as cxxheaderparser can't deal with them
    """
    try:
        pp = CustomPreprocessor()
        if include_paths:
            for p in include_paths:
                pp.add_path(p)

        for define in defines:
            pp.define(define)

        with open(fname, encoding="utf-8-sig") as fp:
            pp_content = fp.read()

        pp.parse(pp_content, fname)

        if pp.errors:
            raise PreprocessorError(f"{fname}: {'\n'.join(pp.errors)}")
        elif pp.return_code:
            raise PreprocessorError(f"{fname}: preprocessor failed with exit code {pp.return_code}")

        fp = io.StringIO()
        pp.write(fp)
        return fp.getvalue()
        
    except PreprocessorError:
        raise 
    except Exception as e:
        raise PreprocessorError(f"{fname}: unexpected preprocessor error") from e



if __name__ == "__main__":
    print(preprocess_file(sys.argv[1], sys.argv[2:]))
