import atexit
import os
from os.path import dirname, exists, join, normpath
import posixpath
import shutil
import sys
import tempfile
import zipfile


from urllib.request import urlretrieve, urlcleanup


def _download(url):
    """
    Downloads a file to a temporary directory
    """

    print("Downloading", url)

    def _reporthook(count, blocksize, totalsize):
        percent = int(count * blocksize * 100 / totalsize)
        sys.stdout.write("\r%02d%%" % percent)
        sys.stdout.flush()

    filename, _ = urlretrieve(url, reporthook=_reporthook)
    sys.stdout.write("\n")
    sys.stdout.flush()
    atexit.register(urlcleanup)
    return filename


def download_and_extract_zip(url, to=None, cache=None):
    """
    Utility method intended to be useful for downloading/extracting
    third party source zipfiles

    :param to: is either a string or a dict of {src: dst}
    """

    if to is None:
        # generate temporary directory
        tod = tempfile.TemporaryDirectory()
        to = tod.name
        atexit.register(tod.cleanup)

    zip_fname = None
    if cache:
        os.makedirs(cache, exist_ok=True)
        cache_fname = join(cache, posixpath.basename(url))
        if not exists(cache_fname):
            zip_fname = _download(url)
            shutil.copy(zip_fname, cache_fname)
        zip_fname = cache_fname
    else:
        zip_fname = _download(url)

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
