#!/usr/bin/env python3

import http.server
import os
from os.path import abspath, dirname, join
import pathlib
import shutil
import sys
import subprocess
import threading
import tempfile
import zipfile


def create_artifact_path(path, group_id, artifact_id, version, classifier):
    components = group_id.split(".") + [artifact_id, version]
    path = join(path, *components)
    os.makedirs(path, exist_ok=True)
    fname = f"{artifact_id}-{version}-{classifier}.zip"
    return join(path, fname)


def http_server():
    httpd = http.server.HTTPServer(
        ("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler
    )

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    return httpd, httpd.socket.getsockname()[1]


if __name__ == "__main__":

    root = abspath(dirname(__file__))
    os.chdir(root)

    # delete build/cache directory
    shutil.rmtree(join(root, "build", "cache"), ignore_errors=True)

    # create tempdir with maven directory structure for pkg
    with tempfile.TemporaryDirectory() as d:

        # create headers and sources zip files
        hname = create_artifact_path(d, "fake.dl", "dl", "1.2.3", "headers")
        with zipfile.ZipFile(hname, "w") as z:
            z.write(join(root, "dl", "downloaded.h"), "downloaded.h")

        sname = create_artifact_path(d, "fake.dl", "dl", "1.2.3", "sources")
        with zipfile.ZipFile(sname, "w") as z:
            z.write(join(root, "dl", "downloaded.cpp"), "downloaded.cpp")

        # http.server prior to 3.7 could only serve the current directory
        os.chdir(d)

        # start http server on random port
        httpd, port = http_server()

        with open(join(root, "pyproject.toml.tmpl")) as rfp:
            content = rfp.read().replace("RANDOM_PORT", str(port))
            with open(join(root, "pyproject.toml"), "w") as wfp:
                wfp.write(content)

        cwd = None

        if len(sys.argv) == 2 and sys.argv[1] == "wheel":
            cmd_args = [sys.executable, "-m", "build", "--wheel", "--no-isolation"]
            cwd = root
        else:
            # run pip install
            cmd_args = [
                sys.executable,
                "-m",
                "pip",
                "-v",
                "--disable-pip-version-check",
                "install",
                "--no-build-isolation",
            ]

            if len(sys.argv) == 2 and sys.argv[1] == "-e":
                cmd_args.append("-e")

            cmd_args.append(root)

        env = os.environ.copy()
        env["SETUPTOOLS_SCM_PRETEND_VERSION"] = "0.0.1"

        subprocess.check_call(cmd_args, cwd=cwd, env=env)

        # Windows fails if you try to delete the directory you're currently in
        os.chdir(root)
