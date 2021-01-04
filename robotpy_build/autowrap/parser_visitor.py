from robotpy_build.autowrap.tmplcontext import (
    EnumContext,
    EnumeratorContext,
    HeaderContext,
)
import typing
from keyword import iskeyword


from cxxheaderparser.types import (
    EnumDecl,
    Field,
    ForwardDecl,
    FriendDecl,
    Function,
    Method,
    Typedef,
    UsingAlias,
    UsingDecl,
    Variable,
)

from cxxheaderparser.parserstate import (
    State,
    EmptyBlockState,
    ClassBlockState,
    ExternBlockState,
    NamespaceBlockState,
)
import sphinxify

from ..config.autowrap_yml import (
    AutowrapConfigYaml,
    BufferType,
    ClassData,
    EnumValue,
    FunctionData,
    PropData,
    PropAccess,
    ReturnValuePolicy,
)
from .generator_data import GeneratorData, MissingReporter
from .mangle import trampoline_signature


def _gen_int_types():
    for i in ("int", "uint"):
        for j in ("", "_fast", "_least"):
            for k in ("8", "16", "32", "64"):
                yield f"{i}{j}{k}_t"
    yield "intmax_t"
    yield "uintmax_t"


_int32_types = set(_gen_int_types())

_rvp_map = {
    ReturnValuePolicy.TAKE_OWNERSHIP: ", py::return_value_policy::take_ownership",
    ReturnValuePolicy.COPY: ", py::return_value_policy::copy",
    ReturnValuePolicy.MOVE: ", py::return_value_policy::move",
    ReturnValuePolicy.REFERENCE: ", py::return_value_policy::reference",
    ReturnValuePolicy.REFERENCE_INTERNAL: ", py::return_value_policy::reference_internal",
    ReturnValuePolicy.AUTOMATIC: "",
    ReturnValuePolicy.AUTOMATIC_REFERENCE: ", py::return_value_policy::automatic_reference",
}

# fmt: off
_operators = {
    # binary
    "-", "+", "*", "/", "%", "&", "^", "==", "!=", "|", ">", ">=", "<", "<=",
    # inplace
    "+=", "-=", "*=", "/=", "%=", "&=", "^=", "|=",
}
# fmt: on


class CxxParserVisitor:

    _qualname_bad = ":<>="
    _qualname_trans = str.maketrans(_qualname_bad, "_" * len(_qualname_bad))

    def __init__(
        self,
        data: AutowrapConfigYaml,
        casters: typing.Dict[str, str],
        report_only: bool,
    ) -> None:
        self.userdata = data
        self.gendata = GeneratorData(data)

        self.context = HeaderContext()

        # self.data = CollectedHeaderData

    def report_missing(self, name: str, reporter: MissingReporter):
        self.gendata.report_missing(name, reporter)

    #
    # Utility functions
    #

    def _add_type_caster(self, typename: str):
        # typename included the namespace, originally the specialization
        # too but we don't need that anymore

        # still need to extract names from each element of the specialization
        # and add those

        # variable[raw_type]
        # fn[returns]
        # parameter[x_type]
        # force_type_casters
        # cls[props][raw_type]

        # defer until the end since there's lots of duplication
        self.types.add(typename)

    # def _get_type_caster_includes(self):
    #     seps = re.compile(r"[<>\(\)]")
    #     includes = set()
    #     for typename in self.types:
    #         tmpl_idx = typename.find("<")
    #         if tmpl_idx == -1:
    #             typenames = [typename]
    #         else:
    #             typenames = [typename[:tmpl_idx]] + seps.split(
    #                 typename[tmpl_idx:].replace(" ", "")
    #             )

    #         for typename in typenames:
    #             if typename:
    #                 header = self.casters.get(typename)
    #                 if header:
    #                     includes.add(header)
    #     return sorted(includes)

    # def _add_subpackage(self, v, data):
    #     if data.subpackage:
    #         var = "pkg_" + data.subpackage.replace(".", "_")
    #         self.subpackages[data.subpackage] = var
    #         v["x_module_var"] = var
    #     else:
    #         v["x_module_var"] = "m"

    def _process_doc(
        self, doxygen: typing.Optional[str], userdata
    ) -> typing.Optional[typing.List[str]]:
        doc = ""
        doc_quoted: typing.Optional[typing.List[str]] = None

        if userdata.doc is not None:
            doc = userdata.doc
        elif doxygen:
            doc = sphinxify.process_raw(doxygen)

        if doc:
            # TODO
            doc = doc.replace("\\", "\\\\").replace('"', '\\"')
            doc_quoted = doc.splitlines(keepends=True)
            doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

        return doc_quoted

    def _cpp2pyname(self, name: str, userdata, strip_prefixes=None, is_operator=False):
        # given a C++ name, convert it to the python name
        if userdata.rename:
            return userdata.rename

        if strip_prefixes is None:
            strip_prefixes = self.userdata.strip_prefixes

        if strip_prefixes:
            for pfx in strip_prefixes:
                if name.startswith(pfx):
                    n = name[len(pfx) :]
                    if n.isidentifier():
                        name = n
                        break

        if iskeyword(name):
            return f"{name}_"
        if not name.isidentifier() and not is_operator:
            raise ValueError(f"name {name!r} is not a valid identifier")

        return name

    #
    # Parser visitor functions
    #

    def on_namespace_start(self, state: NamespaceBlockState) -> None:
        """
        Called when a ``namespace`` directive is encountered
        """

        # update path

    def on_namespace_end(self, state: NamespaceBlockState) -> None:
        """
        Called at the end of a ``namespace`` block
        """

        # unpop path

    def on_function(self, state: State, fn: Function) -> None:
        pass

    def on_using_namespace(self, state: State, namespace: typing.List[str]) -> None:
        ns = "::".join(namespace)
        self.context.using_ns.append(ns)

    def on_using_alias(self, state: State, using: UsingAlias):
        """
        .. code-block:: c++

            using foo = int;

            template <typename T>
            using VectorT = std::vector<T>;

        """

    def on_using_declaration(self, state: State, using: UsingDecl) -> None:
        """
        .. code-block:: c++

            using NS::ClassName;

        """

    #
    # Enums
    #

    def on_enum(self, state: State, enum: EnumDecl) -> None:
        """
        Called after an enum is encountered
        """
        x = state.userdata

        value_prefix = None

        enum.typename

        userdata = self.gendata.get_enum_data(typename, clsname, clsdata)
        if userdata.ignore:
            return

        # if is_class and access == private: return

        # -> for cpp full name, take ns + class into account

        # -> convert typename to name

        # last piece
        py_name = self._cpp2pyname(name, userdata)

        doc = self._process_doc(enum.doxygen, userdata)

        if value_prefix:
            strip_prefixes = [value_prefix + "_", value_prefix]
        else:
            strip_prefixes = []

        values = []
        for ev in enum.values:
            v_cppname = ev.name
            v_userdata = userdata.values.get(v_cppname)
            if v_userdata is None:
                v_userdata = EnumValue()

            if v_userdata.ignore:
                continue

            v_pyname = self._cpp2pyname(v_cppname, v_userdata, strip_prefixes)
            v_doc = self._process_doc(ev.doxygen, v_userdata)
            values.append(EnumeratorContext(v_cppname, v_pyname, v_doc))

        enumcxt = EnumContext(full_cpp_name, py_name, values, doc)

        # needs class context otherwise can't attach to correct scope
        # self.header.enums.append(enumcxt)

    #
    # Class/union/struct
    #

    def on_class_start(self, state: ClassBlockState) -> None:
        """
        Called when a class/struct/union is encountered

        When part of a typedef:

        .. code-block:: c++

            typedef struct { } X;

        This is called first, followed by on_typedef for each typedef instance
        encountered. The compound type object is passed as the type to the
        typedef.
        """

        # if ignored, return

        # if parent access is private, return

    def on_class_field(self, state: ClassBlockState, f: Field) -> None:
        """
        Called when a field of a class is encountered
        """

        # if ignored, return

        # if parent access is private, return

    def on_class_method(self, state: ClassBlockState, method: Method) -> None:
        """
        Called when a method of a class is encountered
        """

        # if ignored, return

        # if parent access is private, return

    #
    # Unused items
    #

    def on_define(self, state: State, content: str) -> None:
        pass  # intentionally empty

    def on_pragma(self, state: State, content: str) -> None:
        pass  # intentionally empty

    def on_include(self, state: State, filename: str) -> None:
        pass  # intentionally empty

    def on_empty_block_start(self, state: EmptyBlockState) -> None:
        pass  # intentionally empty

    def on_empty_block_end(self, state: EmptyBlockState) -> None:
        pass  # intentionally empty

    def on_extern_block_start(self, state: ExternBlockState) -> None:
        pass  # intentionally empty

    def on_extern_block_end(self, state: ExternBlockState) -> None:
        pass  # intentionally empty

    def on_forward_decl(self, state: State, fdecl: ForwardDecl) -> None:
        pass  # intentionally empty
        # TODO: maybe turn these into typealiases since they might be used somewhere

    def on_variable(self, state: State, v: Variable) -> None:
        pass  # intentionally empty, not supported by robotpy-build

    def on_typedef(self, state: State, typedef: Typedef) -> None:
        pass  # intentionally empty

    def on_class_friend(self, state: ClassBlockState, friend: FriendDecl) -> None:
        pass  # intentionally empty

    def on_class_end(self, state: ClassBlockState) -> None:
        pass  # intentionally empty