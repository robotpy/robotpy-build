import typing
from keyword import iskeyword

from cxxheaderparser.parserstate import (
    State,
    EmptyBlockState,
    ClassBlockState,
    ExternBlockState,
    NamespaceBlockState,
)
from cxxheaderparser.tokfmt import tokfmt
from cxxheaderparser.types import (
    Array,
    DecoratedType,
    EnumDecl,
    Field,
    ForwardDecl,
    FriendDecl,
    Function,
    FunctionType,
    FundamentalSpecifier,
    Method,
    NameSpecifier,
    PQName,
    Reference,
    Type,
    Typedef,
    UsingAlias,
    UsingDecl,
    Variable,
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
from .tmplcontext import (
    ClassContext,
    EnumContext,
    EnumeratorContext,
    FieldContext,
    HeaderContext,
)


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


def _is_fundamental(dt: DecoratedType):
    t = dt.get_type()
    if isinstance(t, Type) and not t.typename.classkey:
        last_segment = t.typename.segments[-1]
        if isinstance(last_segment, FundamentalSpecifier):
            return True
        elif (
            isinstance(last_segment, NameSpecifier)
            and last_segment.name in _int32_types
        ):
            return True

    return False


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

        self.path_stack = typing.Deque[str]()
        self.cls_stack = typing.Deque[typing.Optional[ClassContext]]()
        self.cls: typing.Optional[ClassContext] = None

    def report_missing(self, name: str, reporter: MissingReporter):
        self.gendata.report_missing(name, reporter)

    #
    # Utility functions
    #

    def _add_type_caster_pqname(self, typename: PQName):

        segments = []

        # Only add things that are entirely name specifiers, and always omit
        # specializations from the name
        for segment in typename.segments:
            if not isinstance(segment, NameSpecifier):
                return

            segments.append(segment.name)
            specialization = segment.specialization
            if specialization:
                for arg in specialization.args:
                    argg = arg.arg
                    if isinstance(argg, DecoratedType):
                        self._add_type_caster(argg)

        # add the type name to the set to be resolved later
        self.types.add("::".join(segments))

    def _add_type_caster(self, dtype: DecoratedType):
        # convert to a string containing just the name of the type
        t = dtype.get_type()
        if isinstance(t, Type):
            self._add_type_caster_pqname(t.typename)
        elif isinstance(t, FunctionType):
            self._add_type_caster(t.return_type)
            for param in t.parameters:
                self._add_type_caster(param.type)

    def _get_type_caster_includes(self) -> typing.List[str]:
        includes = []
        for typename in self.types:
            header = self.casters.get(typename)
            if header:
                includes.add(header)

        return sorted(includes)

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

    @property
    def path(self) -> str:
        return "::".join(self._path)

    def on_namespace_start(self, state: NamespaceBlockState) -> None:
        ns = "::".join(state.namespace.names)
        self._path.append(ns)

    def on_namespace_end(self, state: NamespaceBlockState) -> None:
        self._path.pop()

    def on_function(self, state: State, fn: Function) -> None:

        # is this a function that belongs to a class? ignore it

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

        parent = self.cls
        self.cls_stack.append(parent)

        decl = state.class_decl

        ignored = False

        # if parent access is private or parent is ignored, set as ignored
        if parent:
            if parent.ignored:
                ignored = True
            elif (
                isinstance(state.parent, ClassBlockState)
                and state.parent.access == "private"
            ):
                ignored = True

        # if ignored, no need to continue processing, but still need to store
        # the context

        # TODO
        self.cls = ClassContext(ignored, cls_key, cls_userdata)

        # scope var set via:
        # {%- if cls.parent -%}
        # {{ cls.parent.x_varname }}
        # {%- elif cls.data.template_params -%}
        # m
        # {%- else -%}
        # {{ cls.x_module_var }}
        # {%- endif -%}

        # for typename in class_data.force_type_casters:
        #     self._add_type_caster(typename)

        # has_constructor = False
        # is_polymorphic = class_data.is_polymorphic

        # # bad assumption? yep
        # if cls["inherits"]:
        #     is_polymorphic = True

        # has_trampoline = (
        #     is_polymorphic and not cls["final"] and not class_data.force_no_trampoline
        # )

        # TODO: if this is a nested class that has a template, don't add it
        #       to the parent's list of children for some reason
        #
        #       .. probably need to add it to the parent's list of templates?

    def _on_class_bases(self, bases):
        pass

        # for each base, construct a qualname for each base

        # check for qualname override
        #

        # for each base parameter, add it to the list

        # is it an ignored base

        # ensure that any specified ignored bases actually existed
        # if ignored_bases:
        #     bases = ", ".join(base["class"] for base in cls["inherits"])
        #     invalid_bases = ", ".join(ignored_bases.keys())
        #     raise ValueError(
        #         f"{cls_name}: ignored_bases contains non-existant bases "
        #         + f"{invalid_bases}; valid bases are {bases}"
        #     )

        # .. x_inherits is what gets set

        # cons

    def on_class_end(self, state: ClassBlockState) -> None:
        # this_cls = self.cls
        self.cls = self.cls_stack.pop()

    def on_class_field(self, state: ClassBlockState, f: Field) -> None:
        """
        Called when a field of a class is encountered
        """

        if self.cls.ignored:
            return

        # if access in "private" or (
        #             access == "protected" and not has_trampoline
        #         ):
        #             v["data"] = PropData(ignore=True)
        #             continue

        if state.access == "private" or (
            state.access == "protected" and state.class_decl.final
        ):
            return

        cpp_name = f.name
        if not cpp_name:
            # can't wrap unnamed fields
            return

        cpp_type = f.type

        is_reference = isinstance(cpp_type, Reference)

        array_size = None
        if isinstance(cpp_type, Array):
            # ignore arrays with incomplete size
            if cpp_type.size is None:
                return

            array_size = tokfmt(cpp_type.size.tokens)
            cpp_type = cpp_type.array_of

            if isinstance(cpp_type, Array):
                # punt on multidimensional arrays for now
                return

        userdata = self.gendata.get_cls_prop_data(cpp_name, cls_key, cls_userdata)
        if userdata.ignore:
            return

        cpp_typename = str(cpp_type)

        if userdata.rename:
            py_name = userdata.rename
        elif state.access == "protected":
            py_name = f"{cpp_name}_"
        else:
            py_name = cpp_name

        if userdata.access == PropAccess.AUTOMATIC:
            # We assume that a struct intentionally has readwrite data
            # attributes regardless of type
            if state.class_decl.classkey != "class":
                readonly = False

            # Properties that aren't fundamental or a reference are readonly unless
            # overridden by the hook configuration
            else:
                readonly = not (
                    isinstance(cpp_type, Reference) or _is_fundamental(cpp_type)
                )

        elif userdata.access == PropAccess.READONLY:
            readonly = True
        else:
            readonly = False

        doc = self._process_doc(f.doxygen, userdata)

        # do something with this
        FieldContext(
            cpp_typename,
            cpp_name,
            py_name,
            readonly,
            f.static,
            is_reference,
            array_size,
            doc,
        )

    def on_class_method(self, state: ClassBlockState, method: Method) -> None:
        """
        Called when a method of a class is encountered
        """

        # if class ignored

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
