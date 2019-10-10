from distutils.core import Command


class BuildDl(Command):

    command_name = "build_dl"
    description = "Downloads files"
    user_options = []
    wrappers = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for wrapper in self.wrappers:
            wrapper.on_build_dl()
