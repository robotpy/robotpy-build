#!/usr/bin/env python3

import os
from os.path import abspath, dirname, join
import pathlib
import shutil
import sys
import subprocess
import tempfile
import zipfile


def subprocess_must_run(*args, **kwargs):
    """Run a subprocess verbosely and exit if there is an error"""
    try:
        print("+", *args[0])
        subprocess.run(check=True, *args, **kwargs)
    except subprocess.CalledProcessError as cbe:
        print(cbe, file=sys.stderr)
        sys.exit(cbe.returncode)


if __name__ == "__main__":
    root = abspath(dirname(__file__))
    os.chdir(root)

    to_install = ["sw-test-base", "sw-caster-consumer", "sw-test"]

    # First, uninstall packages
    subprocess_must_run(
        [sys.executable, "-m", "pip", "--disable-pip-version-check", "uninstall", "-y"]
        + to_install
    )

    # Now install them
    for pkg in to_install:
        subprocess_must_run(
            [
                sys.executable,
                "-m",
                "pip",
                "-v",
                "--disable-pip-version-check",
                "install",
                "--no-build-isolation",
                os.path.abspath(pkg),
            ]
            + sys.argv[1:]
        )
