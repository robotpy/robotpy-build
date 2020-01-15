from distutils.core import Command
import os.path


class BuildDl(Command):

    command_name = "build_dl"
    description = "Downloads files"
    user_options = [
        ("build-base=", "b", "base directory for build library"),
        ("build-cache=", None, "build directory to cache downloaded objects"),
        ("src-unpack-to=", None, "build directory to unpack sources to"),
    ]
    wrappers = []

    def initialize_options(self):
        self.build_base = None
        self.build_cache = None
        self.src_unpack_to = None

    def finalize_options(self):
        self.set_undefined_options("build", ("build_base", "build_base"))
        if self.build_cache is None:
            self.build_cache = os.path.join(self.build_base, "cache")
        if self.src_unpack_to is None:
            self.src_unpack_to = os.path.join(self.build_base, "dlsrc")

    def run(self):
        for wrapper in self.wrappers:
            wrapper.on_build_dl(self.build_cache, self.src_unpack_to)
