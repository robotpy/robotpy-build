#!/usr/bin/env python3

import os
from os.path import abspath, dirname, join
import sys
import subprocess

if __name__ == "__main__":

    root = abspath(dirname(__file__))
    os.chdir(root)

    # Install cpp project
    wcpp = join(root, "cpp", "run_install.py")
    subprocess.check_call([sys.executable, wcpp] + sys.argv[1:])

    # Run pytest
    subprocess.check_call([sys.executable, "-m", "pytest"])
