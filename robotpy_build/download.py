import atexit
import contextlib
import os
from os.path import dirname, exists, join, normpath
import posixpath
import shutil
import sys
import urllib.request
import tempfile
import zipfile

from .version import version


USER_AGENT = f"robotpy-build/{version}"
SHOW_PROGRESS = "CI" not in os.environ


def _download(url: str, dst_fname: str):
    """
    Downloads a file to a specified directory
    """

    def _reporthook(count, blocksize, totalsize):
        if SHOW_PROGRESS:
            percent = int(count * blocksize * 100 / totalsize)
            sys.stdout.write("\r%02d%%" % percent)
            sys.stdout.flush()

    print("Downloading", url)

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with contextlib.closing(urllib.request.urlopen(request)) as fp:
        headers = fp.info()

        with open(dst_fname, "wb") as tfp:

            # copied from urlretrieve source code, Python license
            bs = 1024 * 8
            size = -1
            blocknum = 0
            read = 0
            if "content-length" in headers:
                size = int(headers["Content-Length"])

            while True:
                block = fp.read(bs)
                if not block:
                    break
                read += len(block)
                tfp.write(block)
                blocknum += 1
                if _reporthook:
                    _reporthook(blocknum, bs, size)

    if SHOW_PROGRESS:
        sys.stdout.write("\n")
        sys.stdout.flush()


def download_and_extract_zip(url, to, cache):
    """
    Utility method intended to be useful for downloading/extracting
    third party source zipfiles

    :param to: is either a string or a dict of {src: dst}
    """

    os.makedirs(cache, exist_ok=True)
    zip_fname = join(cache, posixpath.basename(url))
    if not exists(zip_fname):
        _download(url, zip_fname)

    with zipfile.ZipFile(zip_fname) as z:
        if isinstance(to, str):
            to = {"": to}

        for src, dst in to.items():
            if src == "":
                z.extractall(dst)
            else:
                # if is directory, copy whole thing recursively
                try:
                    info = z.getinfo(src)
                except KeyError as e:
                    osrc = src
                    src = src + "/"
                    try:
                        info = z.getinfo(src)
                    except KeyError:
                        info = None
                    if info is None:
                        msg = f"error extracting {osrc} from {zip_fname}"
                        raise ValueError(msg) from e
                if info.is_dir():
                    ilen = len(info.filename)
                    for minfo in z.infolist():
                        if minfo.is_dir():
                            continue
                        srcname = posixpath.normpath(minfo.filename)
                        if srcname.startswith(info.filename):
                            dstname = join(dst, normpath(srcname[ilen:]))
                            dstdir = dirname(dstname)
                            if not exists(dstdir):
                                os.makedirs(dstdir)
                            with z.open(minfo.filename, "r") as zfp, open(
                                dstname, "wb"
                            ) as fp:
                                shutil.copyfileobj(zfp, fp)
                else:
                    # otherwise write a single file
                    with z.open(src, "r") as zfp, open(dst, "wb") as fp:
                        shutil.copyfileobj(zfp, fp)
