import sys
import typing


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
        self.gendata = GeneratorData(data)

        # self.data = CollectedHeaderData

    def report_missing(self, name: str, reporter: MissingReporter):
        self.gendata.report_missing(name, reporter)

    def _process_doc(self, thing, data) -> typing.Optional[typing.List[str]]:
        doc = ""
        doc_quoted: typing.Optional[typing.List[str]] = None

        if data.doc is not None:
            doc = data.doc
        elif "doxygen" in thing:
            doc = thing["doxygen"]
            doc = sphinxify.process_raw(doc)

        if doc:
            # TODO
            doc = doc.replace("\\", "\\\\").replace('"', '\\"')
            doc_quoted = doc.splitlines(keepends=True)
            doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

        return doc_quoted

    def on_define(self, state: State, content: str) -> None:
        pass

    def on_pragma(self, state: State, content: str) -> None:
        pass

    def on_include(self, state: State, filename: str) -> None:
        pass

    def on_empty_block_start(self, state: EmptyBlockState) -> None:
        pass

    def on_empty_block_end(self, state: EmptyBlockState) -> None:
        pass

    def on_extern_block_start(self, state: ExternBlockState) -> None:
        pass

    def on_extern_block_end(self, state: ExternBlockState) -> None:
        pass

    def on_namespace_start(self, state: NamespaceBlockState) -> None:
        """
        Called when a ``namespace`` directive is encountered
        """

    def on_namespace_end(self, state: NamespaceBlockState) -> None:
        """
        Called at the end of a ``namespace`` block
        """

    def on_forward_decl(self, state: State, fdecl: ForwardDecl) -> None:
        """
        Called when a forward declaration is encountered
        """

    def on_variable(self, state: State, v: Variable) -> None:
        pass

    def on_function(self, state: State, fn: Function) -> None:
        pass

    def on_typedef(self, state: State, typedef: Typedef) -> None:
        pass

    def on_using_namespace(self, state: State, namespace: typing.List[str]) -> None:
        """
        .. code-block:: c++

            using namespace std;
        """

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

    def on_class_field(self, state: ClassBlockState, f: Field) -> None:
        """
        Called when a field of a class is encountered
        """

    def on_class_friend(self, state: ClassBlockState, friend: FriendDecl):
        """
        Called when a friend declaration is encountered
        """

    def on_class_method(self, state: ClassBlockState, method: Method) -> None:
        """
        Called when a method of a class is encountered
        """

    def on_class_end(self, state: ClassBlockState) -> None:
        """
        Called when the end of a class/struct/union is encountered.

        When a variable like this is declared:

        .. code-block:: c++

            struct X {

            } x;

        Then ``on_class_start``, .. ``on_class_end`` are emitted, along with
        ``on_variable`` for each instance declared.
        """
