from distutils.core import Command
import os.path


class BuildDl(Command):

    command_name = "build_dl"
    description = "Downloads files"
    user_options = [
        ("build-base=", "b", "base directory for build library"),
        ("build-cache=", "b", "build directory to cache downloaded objects"),
    ]
    wrappers = []

    def initialize_options(self):
        self.build_base = None
        self.build_cache = None

    def finalize_options(self):
        self.set_undefined_options("build", ("build_base", "build_base"))
        if self.build_cache is None:
            self.build_cache = os.path.join(self.build_base, "cache")

    def run(self):
        for wrapper in self.wrappers:
            wrapper.on_build_dl(self.build_cache)
