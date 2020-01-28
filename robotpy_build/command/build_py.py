from typing import List

from setuptools.command.build_py import build_py

from ..wrapper import Wrapper


class BuildPy(build_py):

    wrappers: List[Wrapper] = []

    def run(self):

        # files need to be generated before building can occur
        # -> otherwise they're not included in the bdist
        self.run_command("build_gen")

        # Add the generated files to the package data
        for package, _, _, filenames in self.data_files:
            for wrapper in self.wrappers:
                if wrapper.package_name == package:
                    filenames.extend(wrapper.generated_files)
                    break

        build_py.run(self)
