from os.path import abspath
from setuptools.command.editable_wheel import editable_wheel


class EditableWheel(editable_wheel):
    def run(self):
        # you aren't supposed to do this, but... they broke my workflow
        self.distribution.rpybuild_develop_path = abspath(self.project_dir)
        editable_wheel.run(self)
