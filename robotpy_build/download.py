import atexit
import os
from os.path import exists, join
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
            z.extractall(to)
            return to
        else:
            for src, dst in to.items():
                with z.open(src, "r") as zfp:
                    with open(dst, "wb") as fp:
                        shutil.copyfileobj(zfp, fp)


def download_maven(dlcfg, classifier, to, cache):
    # TODO: support development against locally installed things?
    repo_url = dlcfg.repo_url
    grp = dlcfg.group_id.replace(".", "/")
    art = dlcfg.artifact_id
    ver = dlcfg.version

    url = f"{repo_url}/{grp}/{art}/{ver}/{art}-{ver}-{classifier}.zip"
    return download_and_extract_zip(url, to, cache)
