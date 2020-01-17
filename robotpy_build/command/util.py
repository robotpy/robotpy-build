def get_install_root(cmd):
    # hack
    install_root = getattr(cmd.distribution, "rpybuild_develop_path", None)
    if not install_root:
        inst_command = cmd.distribution.get_command_obj("install")
        inst_command.ensure_finalized()
        install_root = inst_command.install_platlib

    return install_root
