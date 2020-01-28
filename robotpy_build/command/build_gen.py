from distutils.core import Command
from typing import List
import os.path

from ..wrapper import Wrapper


class BuildGen(Command):

    command_name = "build_gen"
    description = "Generates source files"
    user_options = [
        ("build-base=", "b", "base directory for build library"),
        ("build-temp=", "t", "temporary build directory"),
        ("cxx-gen-dir=", "b", "Directory to write generated C++ files"),
    ]
    wrappers: List[Wrapper] = []

    def initialize_options(self):
        self.build_base = None
        self.build_temp = None
        self.cxx_gen_dir = None

    def finalize_options(self):
        self.set_undefined_options(
            "build", ("build_base", "build_base"), ("build_temp", "build_temp")
        )
        if self.cxx_gen_dir is None:
            self.cxx_gen_dir = os.path.join(self.build_temp, "gensrc")

    def run(self):
        # files need to be downloaded before building can occur
        self.run_command("build_dl")

        for wrapper in self.wrappers:
            wrapper.on_build_gen(self.cxx_gen_dir)
