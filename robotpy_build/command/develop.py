from os.path import abspath
from setuptools.command.develop import develop


class Develop(develop):
    def run(self):
        self.distribution.rpybuild_develop_path = abspath(self.egg_base)
        develop.run(self)

        # if not uninstall, perform fixups on OSX?
