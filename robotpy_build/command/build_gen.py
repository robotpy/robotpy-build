from distutils.core import Command


class BuildGen(Command):

    command_name = "build_gen"
    description = "Generates source files"
    user_options = []
    wrappers = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # files need to be downloaded before building can occur
        self.run_command("build_dl")

        for wrapper in self.wrappers:
            wrapper.on_build_gen()
