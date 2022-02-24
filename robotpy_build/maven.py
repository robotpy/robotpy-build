import typing

from .pyproject_configs import Download, MavenLibDownload


def _get_artifact_url(dlcfg: MavenLibDownload, classifier: str) -> str:
    # TODO: support development against locally installed things?
    repo_url = dlcfg.repo_url
    grp = dlcfg.group_id.replace(".", "/")
    art = dlcfg.artifact_id
    ver = dlcfg.version

    return f"{repo_url}/{grp}/{art}/{ver}/{art}-{ver}-{classifier}.zip"


def convert_maven_to_downloads(
    mcfg: MavenLibDownload, static: bool
) -> typing.List[Download]:
    """
    Converts a MavenLibDownload object to a list of normal downloads
    """

    dl_lib = {}
    dl_header = {}
    dl_sources = {}

    if mcfg.use_sources:
        if static:
            raise ValueError("Cannot specify sources in static_lib section")

        # sources don't have libs, ignore them
        dl_sources["url"] = _get_artifact_url(mcfg, mcfg.sources_classifier)
        dl_sources["sources"] = mcfg.sources
        dl_sources["patches"] = mcfg.patches
    elif mcfg.sources is not None:
        raise ValueError("sources must be None if use_sources is False!")
    elif mcfg.patches is not None:
        raise ValueError("patches must be None if use_sources is False!")
    else:
        # libs

        dl_lib["libs"] = mcfg.libs
        if mcfg.libs is mcfg.dlopenlibs is None:
            dl_lib["libs"] = [mcfg.artifact_id]
        dl_lib["dlopenlibs"] = mcfg.dlopenlibs
        dl_lib["libexts"] = mcfg.libexts
        dl_lib["linkexts"] = mcfg.linkexts

        if static:
            dl_lib["libdir"] = "{{ OS }}/{{ ARCH }}/static"
            dl_lib["url"] = _get_artifact_url(mcfg, "{{ OS }}{{ ARCH }}static")
        else:
            dl_lib["libdir"] = "{{ OS }}/{{ ARCH }}/shared"
            dl_lib["url"] = _get_artifact_url(mcfg, "{{ OS }}{{ ARCH }}")

    # headers
    dl_header["incdir"] = ""
    dl_header["url"] = _get_artifact_url(mcfg, "headers")
    dl_header["header_patches"] = mcfg.header_patches

    # Construct downloads and return it
    downloads = []
    for d in (dl_lib, dl_header, dl_sources):
        if d:
            downloads.append(Download(**d))

    return downloads
