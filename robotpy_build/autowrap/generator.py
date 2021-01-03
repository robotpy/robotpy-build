from os.path import join, relpath
import typing
import pathlib

from cxxheaderparser.parser import CxxParser
from cxxheaderparser.visitor import CxxVisitor

import jinja2

from ..config.autowrap_yml import AutowrapConfigYaml
from .preprocessor import preprocess_file

templates_path = pathlib.Path(__file__).parent.absolute() / "templates"


class WrapperGenerator:
    """
    Generates files from data + templates
    """

    def __init__(self) -> None:

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=templates_path),
            undefined=jinja2.StrictUndefined,
            autoescape=False,
            auto_reload=False,
            # trim_blocks=True,
            # lstrip_blocks=True,
        )

    def parse_header(
        self,
        header_path: str,
        pp_include_paths: typing.List[str],
        pp_defines: typing.List[str],
        visitor: CxxVisitor,
    ) -> None:
        # preprocess it
        content = preprocess_file(header_path, pp_include_paths, pp_defines)

        # Parse it using the passed in visitor
        parser = CxxParser(header_path, content, visitor)
        parser.parse()

    def write_files(
        self, data, name: str, cxx_gen_dir: str, hpp_gen_dir: str
    ) -> typing.Tuple[str, str]:
        pass

        cpp_dst = join(cxx_gen_dir, f"{name}.cpp")

        classdeps_dst = join(cxx_gen_dir, f"{name}.json")

        hpp_dst = join(
            hpp_gen_dir,
            "{{ cls['namespace'] | replace(':', '_') }}__{{ cls['name'] }}.hpp",
        )

        # collect written hpp files somewhere

        # return generated files
        # -> cpp: one per header cls.cpp.j2
        # -> json: one per header clsdeps.json.j2
        # -> hpp: one per class cls_rpy_include.hpp.j2

        # returns cpp_dst, classdeps_dst

        for tmpl in cfg.templates:
            self._render_template(tmpl, gbls)

        if cfg.class_templates:
            for header in data["headers"]:
                for clsdata in header.classes:
                    gbls["cls"] = clsdata
                    for tmpl in cfg.class_templates:
                        self._render_template(tmpl, gbls)

    def _render_template(self, tmpl_src: str, dst: str, **data):
        jtmpl = self.env.get_template(tmpl_src)
        content = jtmpl.render(**data)
        with open(dst, "w", encoding="utf-8") as fp:
            fp.write(content)
