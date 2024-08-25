#
# Uses cxxheaderparser to parse a header file and outputs a HeaderContext
# suitable for use with the autowrap templates
#

import dataclasses
import pathlib
import re
import sys
import typing
from keyword import iskeyword

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    Protocol = object  # pragma: no cover


import sphinxify
from cxxheaderparser.options import ParserOptions
from cxxheaderparser.parser import CxxParser
from cxxheaderparser.parserstate import (
    ClassBlockState,
    ExternBlockState,
    NamespaceBlockState,
)
from cxxheaderparser.tokfmt import tokfmt
from cxxheaderparser.types import (
    AnonymousName,
    Array,
    ClassDecl,
    Concept,
    DecoratedType,
    EnumDecl,
    Field,
    ForwardDecl,
    FriendDecl,
    Function,
    FunctionType,
    FundamentalSpecifier,
    Method,
    MoveReference,
    NamespaceAlias,
    NameSpecifier,
    Parameter,
    Pointer,
    PQName,
    PQNameSegment,
    Reference,
    TemplateInst,
    Type,
    Typedef,
    UsingAlias,
    UsingDecl,
    Value,
    Variable,
)

from ..config.autowrap_yml import (
    AutowrapConfigYaml,
    BufferData,
    BufferType,
    ClassData,
    EnumValue,
    FunctionData,
    ParamData,
    PropAccess,
    ReturnValuePolicy,
)
from .generator_data import GeneratorData, OverloadTracker
from .j2_context import (
    BaseClassData,
    ClassContext,
    ClassTemplateData,
    Documentation,
    EnumContext,
    EnumeratorContext,
    FunctionContext,
    GeneratedLambda,
    HeaderContext,
    ParamCategory,
    ParamContext,
    PropContext,
    TemplateInstanceContext,
    TrampolineData,
)
from .mangle import trampoline_signature


class HasSubpackage(Protocol):
    subpackage: typing.Optional[str]


class HasDoc(Protocol):
    doc: str
    doc_append: str


class HasNameData(Protocol):
    rename: str


# TODO: this isn't the best solution
def _gen_int_types():
    for i in ("int", "uint"):
        for j in ("", "_fast", "_least"):
            for k in ("8", "16", "32", "64"):
                yield f"{i}{j}{k}_t"
    yield "intmax_t"
    yield "uintmax_t"


_int32_types = frozenset(_gen_int_types())


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

_type_caster_seps = re.compile(r"[<>\(\)]")

_qualname_bad = ":<>="
_qualname_trans = str.maketrans(_qualname_bad, "_" * len(_qualname_bad))

_lambda_predent = "          "

_default_param_data = ParamData()
_default_enum_value = EnumValue()


def _is_fundamental(n: PQNameSegment):
    return isinstance(n, FundamentalSpecifier) or (
        isinstance(n, NameSpecifier) and n.name in _int32_types
    )


def _is_prop_readonly(dt: DecoratedType) -> bool:
    t: typing.Union[DecoratedType, FunctionType] = dt
    while True:
        if isinstance(t, Array):
            return False
        elif isinstance(t, (FunctionType, MoveReference, Reference)):
            return False
        elif isinstance(t, Type):
            return not _is_fundamental(t.typename.segments[-1])
        elif isinstance(t, Pointer):
            t = t.ptr_to
        else:
            assert False


def _count_and_unwrap(
    dt: DecoratedType,
) -> typing.Tuple[typing.Union[Array, FunctionType, Type], int, int, bool]:
    ptrs = 0
    refs = 0
    const = False
    t: typing.Union[DecoratedType, FunctionType] = dt
    while True:
        if isinstance(t, Type):
            const = const or t.const
            return t, ptrs, refs, const
        elif isinstance(t, (Array, FunctionType)):
            return t, ptrs, refs, const
        elif isinstance(t, Pointer):
            ptrs += 1
            const = const or t.const
            t = t.ptr_to
        elif isinstance(t, Reference):
            refs += 1
            t = t.ref_to
        elif isinstance(t, MoveReference):
            refs += 2
            t = t.moveref_to
        else:
            assert False


def _fmt_base_name(typename: PQName) -> typing.Tuple[str, str, str, typing.List[str]]:
    all_parts = []
    nameonly_parts = []

    for segment in typename.segments[:-1]:
        if not isinstance(segment, NameSpecifier):
            raise ValueError(f"base name formatting will fail for {typename.format()}")
        all_parts.append(segment.format())
        nameonly_parts.append(segment.name)

    last_segment = typename.segments[-1]
    if not isinstance(last_segment, NameSpecifier):
        raise ValueError(f"base name formatting will fail for {typename.format()}")

    nameonly_parts.append(last_segment.name)

    if last_segment.specialization:
        most_parts = all_parts[:-1]
        all_parts.append(last_segment.format())
        most_parts.append(last_segment.name)
        tparam_list = [arg.format() for arg in last_segment.specialization.args]
    else:
        all_parts.append(last_segment.name)
        most_parts = all_parts
        tparam_list = []

    return (
        "::".join(most_parts),
        "::".join(all_parts),
        "::".join(nameonly_parts),
        tparam_list,
    )

    # returns all names, with specialization for everything except the last
    # returns all names + specialization
    # returns list of all specialization parameters

    # cpp_name, cpp_name_w_templates, tparam_list

    assert False


T = typing.TypeVar("T")


def _fmt_nameonly(typename: PQName) -> str:
    """
    Not particularly general
    """
    parts = []
    for segment in typename.segments:
        if not isinstance(segment, NameSpecifier):
            return ""
        parts.append(segment.name)
    return "::".join(parts)


def _fmt_array_size(t: Array) -> typing.Optional[int]:
    if t.size:
        sz = tokfmt(t.size.tokens)
        try:
            return int(sz)
        except ValueError:
            pass

    return None


@dataclasses.dataclass
class _ReturnParamContext:
    #: was x_type
    cpp_type: str

    #: If this is an out parameter, the name of the parameter
    cpp_retname: str


def _using_signature(cls: ClassContext, fn: FunctionContext) -> str:
    return f"{cls.full_cpp_name_identifier}_{fn.cpp_name}"


#
# Visitor implementation
#


class ClassStateData(typing.NamedTuple):
    ctx: ClassContext
    cls_key: str
    data: ClassData

    typealias_names: typing.Set[str]

    # have to defer processing these
    defer_protected_methods: typing.List[Method]
    defer_private_nonvirtual_methods: typing.List[Method]
    defer_private_virtual_methods: typing.List[Method]
    defer_protected_fields: typing.List[Field]

    # Needed for trampoline
    cls_cpp_identifier: str
    template_argument_list: str
    base_template_params: str
    base_template_args: str

    # See j2_context::TrampolineData for these
    methods_to_disable: typing.List[FunctionContext]
    virtual_methods: typing.List[FunctionContext]
    protected_constructors: typing.List[FunctionContext]
    non_virtual_protected_methods: typing.List[FunctionContext]


Context = typing.Union[str, ClassStateData]

# define what user_data we store in each state type
# - classes are ClassStateData
# - everything else is the current namespace name
AWExternBlockState = ExternBlockState[str, str]
AWNamespaceBlockState = NamespaceBlockState[str, str]
AWClassBlockState = ClassBlockState[ClassStateData, Context]

AWState = typing.Union[AWExternBlockState, AWNamespaceBlockState, AWClassBlockState]
AWNonClassBlockState = typing.Union[AWExternBlockState, AWNamespaceBlockState]


class AutowrapVisitor:
    """
    Collects the results of parsing a header file
    """

    types: typing.Set[str]
    user_types: typing.Set[str]

    def __init__(
        self,
        hctx: HeaderContext,
        gendata: GeneratorData,
        casters: typing.Dict[str, typing.Dict[str, typing.Any]],
        report_only: bool,
    ) -> None:
        self.hctx = hctx
        self.gendata = gendata
        self.user_cfg = gendata.data
        self.report_only = report_only
        self.casters = casters
        self.types = set()
        self.user_types = set()

    #
    # Visitor interface
    #

    def on_parse_start(self, state: AWNamespaceBlockState) -> None:
        state.user_data = ""

    def on_pragma(self, state: AWState, content: Value) -> None:
        pass

    def on_include(self, state: AWState, filename: str) -> None:
        pass

    def on_extern_block_start(self, state: AWExternBlockState) -> None:
        state.user_data = state.parent.user_data

    def on_extern_block_end(self, state: AWExternBlockState) -> None:
        pass

    def on_namespace_start(self, state: AWNamespaceBlockState) -> None:
        parent_ns = typing.cast(str, state.parent.user_data)
        names = state.namespace.names
        if not names:
            # anonymous namespace items are referenced using the parent
            ns = parent_ns
        elif not parent_ns:
            ns = "::".join(names)
        else:
            ns = f"{parent_ns}::{'::'.join(names)}"

        state.user_data = ns

        if ns not in self.hctx.namespaces:
            self.hctx.namespaces.append(ns)

    def on_namespace_end(self, state: AWNamespaceBlockState) -> None:
        pass

    def on_namespace_alias(
        self, state: AWNonClassBlockState, alias: NamespaceAlias
    ) -> None:
        # TODO: add to some sort of resolver?
        pass

    def on_concept(self, state: AWNonClassBlockState, concept: Concept) -> None:
        pass

    def on_forward_decl(self, state: AWState, fdecl: ForwardDecl) -> None:
        # TODO: add to some sort of resolver?
        pass

    def on_template_inst(self, state: AWState, inst: TemplateInst) -> None:
        pass

    def on_variable(self, state: AWState, v: Variable) -> None:
        # TODO: robotpy-build doesn't wrap global variables at this time
        pass

    def on_function(self, state: AWNonClassBlockState, fn: Function) -> None:
        # operators that aren't class members aren't rendered
        if fn.operator:
            return

        # ignore functions with complicated names
        fn_name = self._get_fn_name(fn)
        if not fn_name:
            return

        data, overload_tracker = self.gendata.get_function_data(fn_name, fn)
        if data.ignore:
            return

        scope_var = self._get_module_var(data)
        fctx = self._on_fn_or_method(
            fn, data, fn_name, scope_var, False, overload_tracker
        )
        fctx.namespace = state.user_data
        self.hctx.functions.append(fctx)

    def on_method_impl(self, state: AWNonClassBlockState, method: Method) -> None:
        # we only wrap methods when defined in a class
        pass

    def on_typedef(self, state: AWState, typedef: Typedef) -> None:
        pass

    def on_using_namespace(
        self, state: AWNonClassBlockState, namespace: typing.List[str]
    ) -> None:
        pass

    def on_using_alias(self, state: AWState, using: UsingAlias) -> None:
        self._add_type_caster(using.type)

        # autodetect embedded using directives, but don't override anything
        # the user specifies
        # - these are in block scope, so they cannot include templates
        if (
            isinstance(state, ClassBlockState)
            and using.access == "public"
            and using.template is None
            and using.alias not in state.user_data.typealias_names
        ):
            ctx = state.user_data.ctx
            ctx.auto_typealias.append(
                f"using {using.alias} [[maybe_unused]] = typename {ctx.full_cpp_name}::{using.alias}"
            )

    def on_using_declaration(self, state: AWState, using: UsingDecl) -> None:
        self._add_type_caster_pqname(using.typename)

        if using.access is None:
            self.hctx.using_declarations.append(using.typename)
        elif isinstance(state, ClassBlockState):
            # A using declaration might bring in a colliding name for a function,
            # so mark it as overloaded
            lseg = using.typename.segments[-1]
            if isinstance(lseg, NameSpecifier):
                cdata = state.user_data
                name = lseg.name
                self.gendata.add_using_decl(
                    name, cdata.cls_key, cdata.data, state.access == "private"
                )

    #
    # Enums
    #

    def on_enum(self, state: AWState, enum: EnumDecl) -> None:
        # If an enum name has more than one component, that's weird and we're
        # not going to support it for now. Who forward declares enums anyways?
        name_segs = enum.typename.segments
        assert len(name_segs) > 0

        if len(name_segs) > 1:
            return
        elif isinstance(name_segs[0], NameSpecifier):
            ename = name_segs[0].name
        elif isinstance(name_segs[0], AnonymousName):
            ename = ""
        else:
            # something else weird we can't support for now
            return

        user_data = state.user_data

        if isinstance(user_data, str):
            # global enum

            enum_data = self.gendata.get_enum_data(ename)
            if enum_data.ignore:
                return

            ctxlist = self.hctx.enums
            var_name = f"enum{len(ctxlist)}"
            enum_scope = user_data
            scope_var = self._get_module_var(enum_data)
        else:
            # per-class -- ignore private/protected enums
            if enum.access != "public":
                return

            enum_data = self.gendata.get_cls_enum_data(
                ename, user_data.cls_key, user_data.data
            )
            if enum_data.ignore:
                return

            cls_ctx = user_data.ctx

            if ename:
                ctxlist = cls_ctx.enums
                var_name = f"{cls_ctx.var_name}_enum{len(ctxlist)}"
            else:
                ctxlist = cls_ctx.unnamed_enums
                var_name = f"{cls_ctx.var_name}_enum_u{len(ctxlist)}"

            enum_scope = cls_ctx.full_cpp_name
            scope_var = cls_ctx.var_name

        value_prefix = None
        strip_prefixes = []
        values: typing.List[EnumeratorContext] = []

        py_name = ""
        full_cpp_name = ""

        if ename:
            full_cpp_name = f"{enum_scope}::{ename}"
            py_name = self._make_py_name(ename, enum_data)

            value_prefix = enum_data.value_prefix
            if not value_prefix:
                value_prefix = ename

            strip_prefixes = [f"{value_prefix}_", value_prefix]
        else:
            full_cpp_name = enum_scope

        for v in enum.values:
            name = v.name
            v_data = enum_data.values.get(name, _default_enum_value)
            if v_data.ignore:
                continue

            values.append(
                EnumeratorContext(
                    full_cpp_name=f"{full_cpp_name}::{name}",
                    py_name=self._make_py_name(name, v_data, strip_prefixes),
                    doc=self._process_doc(v.doxygen, v_data, append_prefix="  "),
                )
            )

        ctxlist.append(
            EnumContext(
                scope_var=scope_var,
                var_name=var_name,
                cpp_name=ename,
                full_cpp_name=full_cpp_name,
                py_name=py_name,
                values=values,
                doc=self._process_doc(enum.doxygen, enum_data),
                arithmetic=enum_data.arithmetic,
                inline_code=enum_data.inline_code,
            )
        )

    #
    # Class/union/struct
    #

    def on_class_start(self, state: AWClassBlockState) -> typing.Optional[bool]:
        # parse everything there is to parse about the declaration
        # of this class, and append it

        # ignore non-public nested classes or classes that have ignored parents
        if state.typedef or (
            isinstance(state.parent, ClassBlockState)
            and state.parent.access != "public"
        ):
            return False

        cls_name_result = self._process_class_name(state)
        if cls_name_result is None:
            return False

        cls_key, cls_name, cls_namespace, parent_ctx = cls_name_result
        class_data = self.gendata.get_class_data(cls_key)

        # Ignore explicitly ignored classes
        if class_data.ignore:
            return False

        for typename in class_data.force_type_casters:
            self._add_user_type_caster(typename)

        class_decl = state.class_decl
        var_name = f"cls_{cls_name}"

        if parent_ctx:
            cls_qualname = f"{parent_ctx.full_cpp_name}::{cls_name}"
            dep_cpp_name = f"{parent_ctx.dep_cpp_name}::{cls_name}"
            scope_var = parent_ctx.var_name
        else:
            cls_qualname = f"{cls_namespace}::{cls_name}"
            dep_cpp_name = cls_qualname
            scope_var = self._get_module_var(class_data)

        cls_cpp_identifier = cls_qualname.translate(_qualname_trans)

        #
        # Process inheritance
        #

        bases, pybase_params = self._process_class_bases(
            cls_namespace, cls_name, class_decl, class_data
        )

        # All names used here should not have any specializations in them
        self.hctx.class_hierarchy[dep_cpp_name] = [
            base.dep_cpp_name for base in bases
        ] + class_data.force_depends

        #
        # Process template parameters
        #

        # <N, .. >
        template_argument_list = ""
        # <typename N, .. >
        template_parameter_list = ""

        template_data: typing.Optional[ClassTemplateData] = None

        if class_data.template_params:
            if class_data.subpackage:
                raise ValueError(
                    f"{cls_name}: classes with subpackages must define subpackage on template instantiation"
                )

            template_args = []
            template_params = []

            base_template_args = []
            base_template_params = []

            # TODO: should be able to remove this parsing since cxxheaderparser
            #       can figure it out for us

            for param in class_data.template_params:
                if " " in param:
                    arg = param.split(" ", 1)[1]
                else:
                    arg = param
                    param = f"typename {param}"

                template_args.append(arg)
                template_params.append(param)

                if arg in pybase_params:
                    base_template_args.append(arg)
                    base_template_params.append(param)

            template_argument_list = ", ".join(template_args)
            template_parameter_list = ", ".join(template_params)

            template_data = ClassTemplateData(
                argument_list=template_argument_list,
                parameter_list=template_parameter_list,
                inline_code=class_data.template_inline_code,
            )

            cls_qualname = f"{cls_qualname}<{template_argument_list}>"

            base_template_params_s = ", ".join(base_template_params)
            base_template_args_s = ", ".join(base_template_args)
        else:
            base_template_params_s = ""
            base_template_args_s = ""

        if not self.report_only:
            if class_decl.template:
                if template_parameter_list == "":
                    raise ValueError(
                        f"{cls_name}: must specify template_params for templated class, or ignore it"
                    )
            else:
                if template_parameter_list != "":
                    raise ValueError(
                        f"{cls_name}: cannot specify template_params for non-template class"
                    )

        #
        # Other stuff
        #

        if class_data.is_polymorphic is not None:
            is_polymorphic = class_data.is_polymorphic
        else:
            # bad assumption? probably
            is_polymorphic = len(class_decl.bases) > 0

        doc = self._process_doc(class_decl.doxygen, class_data)
        py_name = self._make_py_name(cls_name, class_data)

        constants: typing.List[typing.Tuple[str, str]] = []
        for constant in class_data.constants:
            name = constant.split("::")[-1]
            constants.append((name, constant))

        # do logic for extracting user defined typealiases here
        # - these are at class scope, so they can include template
        typealias_names: typing.Set[str] = set()
        user_typealias: typing.List[str] = []
        self._extract_typealias(class_data.typealias, user_typealias, typealias_names)

        ctx = ClassContext(
            parent=parent_ctx,
            namespace=cls_namespace,
            cpp_name=cls_name,
            full_cpp_name=cls_qualname,
            full_cpp_name_identifier=cls_cpp_identifier,
            dep_cpp_name=dep_cpp_name,
            py_name=py_name,
            scope_var=scope_var,
            var_name=var_name,
            nodelete=class_data.nodelete,
            final=class_decl.final,
            doc=doc,
            bases=bases,
            template=template_data,
            user_typealias=user_typealias,
            constants=constants,
            inline_code=class_data.inline_code or "",
            force_multiple_inheritance=class_data.force_multiple_inheritance,
            is_polymorphic=is_polymorphic,
        )

        # Add to parent class or global class list
        if parent_ctx:
            parent_ctx.child_classes.append(ctx)
        else:
            self.hctx.classes.append(ctx)

        # Store for other events to use
        state.user_data = ClassStateData(
            ctx=ctx,
            cls_key=cls_key,
            data=class_data,
            typealias_names=typealias_names,
            # Method data
            defer_protected_methods=[],
            defer_private_nonvirtual_methods=[],
            defer_private_virtual_methods=[],
            defer_protected_fields=[],
            # Trampoline data
            cls_cpp_identifier=cls_cpp_identifier,
            template_argument_list=template_argument_list,
            base_template_args=base_template_args_s,
            base_template_params=base_template_params_s,
            methods_to_disable=[],
            virtual_methods=[],
            protected_constructors=[],
            non_virtual_protected_methods=[],
        )

    def _process_class_name(
        self, state: AWClassBlockState
    ) -> typing.Optional[typing.Tuple[str, str, str, typing.Optional[ClassContext]]]:
        class_decl = state.class_decl
        segments = class_decl.typename.segments
        assert len(segments) > 0

        segment_names: typing.List[str] = []
        for segment in segments:
            if not isinstance(segment, NameSpecifier):
                raise ValueError(
                    f"not sure how to handle '{class_decl.typename.format()}'"
                )
            # ignore specializations for now
            if segment.specialization is not None:
                return None
            segment_names.append(segment.name)

        cls_name = segment_names[-1]
        extra_segments = "::".join(segment_names[:-1])

        parent_ctx: typing.Optional[ClassContext] = None

        parent = state.parent

        if not isinstance(parent, ClassBlockState):
            # easy case -- namespace is the next user_data up
            cls_key = cls_name
            cls_namespace = typing.cast(str, parent.user_data)
            if extra_segments:
                cls_namespace = f"{cls_namespace}::{extra_segments}"
        else:
            # Use things the parent already computed
            cdata = typing.cast(ClassStateData, parent.user_data)
            # parent: AWClassBlockState = state.parent
            parent_ctx = cdata.ctx
            # the parent context already computed namespace, so use that
            if extra_segments:
                cls_key = f"{cdata.cls_key}::{extra_segments}::{cls_name}"
            else:
                cls_key = f"{cdata.cls_key}::{cls_name}"
            cls_namespace = parent_ctx.namespace

        return cls_key, cls_name, cls_namespace, parent_ctx

    def _process_class_bases(
        self,
        cls_namespace: str,
        cls_name: str,
        class_decl: ClassDecl,
        class_data: ClassData,
    ) -> typing.Tuple[
        typing.List[BaseClassData],
        typing.Set[str],
    ]:
        bases: typing.List[BaseClassData] = []
        pybase_params: typing.Set[str] = set()
        ignored_bases = {ib: True for ib in class_data.ignored_bases}

        for base in class_decl.bases:
            if base.access == "private":
                continue

            cpp_name, cpp_name_w_templates, dep_cpp_name, tparam_list = _fmt_base_name(
                base.typename
            )
            if ignored_bases.pop(cpp_name_w_templates, None):
                continue

            # Sometimes, we can't guess all the information about the base, so the
            # user needs to specify it explicitly.
            user_bqual = class_data.base_qualnames.get(cpp_name)
            if user_bqual:
                cpp_name_w_templates = user_bqual
                # TODO: sometimes need to add this to pybase_params, but
                # that would require parsing this more. Seems sufficiently
                # obscure, going to omit it for now.
                tp = user_bqual.find("<")
                if tp == -1:
                    cpp_name = user_bqual
                    template_params = ""
                else:
                    cpp_name = user_bqual[:tp]
                    template_params = user_bqual[tp + 1 : -1]
                dep_cpp_name = cpp_name
            else:
                # TODO: we don't handle nested child classes with templates here
                #       ... but that has to be rather obscure?

                for param in tparam_list:
                    pybase_params.add(param)

                template_params = ", ".join(tparam_list)

                # If no explicit namespace specified, we assume base classes
                # live in the same namespace as the class
                if len(base.typename.segments) == 1:
                    cpp_name = f"{cls_namespace}::{cpp_name}"
                    cpp_name_w_templates = f"{cls_namespace}::{cpp_name_w_templates}"
                    dep_cpp_name = f"{cls_namespace}::{dep_cpp_name}"

            base_identifier = cpp_name.translate(_qualname_trans)

            bases.append(
                BaseClassData(
                    full_cpp_name=cpp_name,
                    full_cpp_name_w_templates=cpp_name_w_templates,
                    full_cpp_name_identifier=base_identifier,
                    dep_cpp_name=dep_cpp_name,
                    template_params=template_params,
                )
            )

        if not self.report_only and ignored_bases:
            bases_s = ", ".join(base.typename.format() for base in class_decl.bases)
            invalid_bases = ", ".join(ignored_bases.keys())
            raise ValueError(
                f"{cls_name}: ignored_bases contains non-existant bases "
                + f"{invalid_bases}; valid bases are {bases_s}"
            )

        return bases, pybase_params

    def on_class_field(self, state: AWClassBlockState, f: Field) -> None:
        # Ignore unnamed fields
        if not f.name:
            return

        access = f.access
        if access == "public":
            self._on_class_field(state, f, state.user_data.ctx.public_properties)
        elif access == "protected":
            state.user_data.defer_protected_fields.append(f)

    def _on_class_field(
        self, state: AWClassBlockState, f: Field, props: typing.List[PropContext]
    ) -> None:
        prop_name = f.name
        if prop_name is None:
            return

        propdata = self.gendata.get_cls_prop_data(
            prop_name, state.user_data.cls_key, state.user_data.data
        )
        if propdata.ignore:
            return

        self._add_type_caster(f.type)
        if propdata.rename:
            py_name = propdata.rename
        elif f.access != "public":
            py_name = f"_{prop_name}"
        elif iskeyword(prop_name):
            py_name = f"{prop_name}_"
        else:
            py_name = prop_name

        if propdata.access == PropAccess.AUTOMATIC:
            # const variables can't be written
            if f.constexpr or getattr(f.type, "const", False):
                prop_readonly = True
            # We assume that a struct intentionally has readwrite data
            # attributes regardless of type
            elif state.class_decl.classkey != "class":
                prop_readonly = False
            else:
                prop_readonly = _is_prop_readonly(f.type)
        else:
            prop_readonly = propdata.access == PropAccess.READONLY

        doc = self._process_doc(f.doxygen, propdata)

        array_size = None
        is_array = False

        if isinstance(f.type, Array):
            is_array = True
            array_size = _fmt_array_size(f.type)
            cpp_type = f.type.array_of.format()
        else:
            cpp_type = f.type.format()

        props.append(
            PropContext(
                py_name=py_name,
                cpp_name=prop_name,
                cpp_type=cpp_type,
                readonly=prop_readonly,
                doc=doc,
                array_size=array_size,
                array=is_array,
                reference=isinstance(f.type, Reference),
                static=f.static,
                bitfield=f.bits is not None,
            )
        )

        # If it's constexpr, insert into the binding scope
        if f.access == "public" and f.constexpr:
            cctx = state.user_data.ctx
            cctx.auto_typealias.append(
                f"static constexpr auto {prop_name} [[maybe_unused]] = {cctx.full_cpp_name}::{prop_name}"
            )

    def on_class_method(self, state: AWClassBlockState, method: Method) -> None:
        # This needs to only process enough about the method to answer things
        # that are needed in on_class_end. Some methods are only processed in
        # on_class_end if the answers are right
        cdata = state.user_data
        cctx = cdata.ctx

        if method.constructor:
            cctx.has_constructor = True
        is_polymorphic = method.virtual or method.override or method.final
        if is_polymorphic:
            cctx.is_polymorphic = True

        access = state.access
        if access == "public":
            # Go ahead and process public methods now
            self._on_class_method(state, method, cctx.wrapped_public_methods)
        elif access == "protected":
            cdata.defer_protected_methods.append(method)
        elif access == "private":
            if is_polymorphic:
                cdata.defer_private_virtual_methods.append(method)
            else:
                cdata.defer_private_nonvirtual_methods.append(method)

    def _on_class_method(
        self,
        state: AWClassBlockState,
        method: Method,
        methods: typing.List[FunctionContext],
    ) -> None:
        cdata = state.user_data
        cctx = cdata.ctx

        # I think this is always true?
        assert len(method.name.segments) == 1

        method_name = self._get_fn_name(method)
        if not method_name:
            return

        is_constructor = method.constructor
        is_override = method.override
        is_virtual = method.virtual or is_override

        operator = method.operator

        # Ignore some operators, deleted methods, destructors
        if (
            (operator and operator not in _operators)
            or method.destructor
            or method.deleted
        ):
            return

        # Also ignore move constructors and copy constructors
        if (
            is_constructor
            and len(method.parameters) == 1
            and self._is_copy_move_constructor(cctx, method.parameters[0].type)
        ):
            return

        is_final = method.final
        is_private = state.access == "private"

        method_data, overload_tracker = self.gendata.get_function_data(
            method_name,
            method,
            cdata.cls_key,
            cdata.data,
            state.access == "private",
        )
        if method_data.ignore:
            return

        fctx = self._on_fn_or_method(
            method,
            method_data,
            method_name,
            cdata.ctx.scope_var,
            state.access != "public",
            overload_tracker,
        )

        # Update class-specific method attributes
        fctx.is_constructor = is_constructor
        if operator:
            fctx.operator = operator
            self.hctx.need_operators_h = True
            if method_data.no_release_gil is None:
                fctx.release_gil = False

            # Use cpp_code to setup the operator
            if fctx.cpp_code is None:
                if len(method.parameters) == 0:
                    fctx.cpp_code = f"{operator} py::self"
                else:
                    ptype, _, _, _ = _count_and_unwrap(method.parameters[0].type)
                    if (
                        isinstance(ptype, Type)
                        and isinstance(ptype.typename.segments[-1], NameSpecifier)
                        and ptype.typename.segments[-1].name == cdata.ctx.cpp_name
                    ):
                        # don't try to predict the type, use py::self instead
                        fctx.cpp_code = f"py::self {operator} py::self"
                    else:
                        fctx.cpp_code = f"py::self {operator} {fctx.all_params[0].cpp_type_no_const}()"

        if method.const:
            fctx.const = True
        if method.static:
            fctx.is_static_method = True
        if method.pure_virtual:
            fctx.is_pure_virtual = True
        if method.ref_qualifier:
            fctx.ref_qualifiers = method.ref_qualifier

        # automatically retain references passed to constructors if the
        # user didn't specify their own keepalive
        if is_constructor and not method_data.keepalive:
            for i, pctx in enumerate(fctx.filtered_params):
                if pctx.full_cpp_type.endswith("&"):
                    fctx.keepalives.append((1, i + 2))

        # Update method lists
        if is_private and is_override:
            cdata.methods_to_disable.append(fctx)
        else:
            if is_final:
                cdata.methods_to_disable.append(fctx)

            # disable virtual method generation for functions with buffer
            # parameters (doing it correctly is hard, so we skip it)
            if is_virtual and not fctx.has_buffers:
                cdata.virtual_methods.append(fctx)

            if not is_private:
                if not fctx.ignore_py:
                    methods.append(fctx)

                if state.access == "protected":
                    if is_constructor:
                        cdata.protected_constructors.append(fctx)
                    elif not is_virtual:
                        cdata.non_virtual_protected_methods.append(fctx)

        # If the method has cpp_code defined, it must either match the function
        # signature of the method, or virtual_xform must be defined with an
        # appropriate conversion. If neither of these are true, it will lead
        # to difficult to diagnose errors at runtime. We add a static assert
        # to try and catch these errors at compile time
        need_vcheck = (
            is_virtual
            and method_data.cpp_code
            and not method_data.virtual_xform
            and not method_data.trampoline_cpp_code
            and not state.class_decl.final
            and not cdata.data.force_no_trampoline
        )
        if need_vcheck:
            cctx.vcheck_fns.append(fctx)
            self.hctx.has_vcheck = True

        # Check for user data errors
        if not self.report_only:
            if method_data.ignore_pure and not method.pure_virtual:
                raise ValueError(
                    f"{cdata.cls_key}::{method_name}: cannot specify ignore_pure for function that isn't pure"
                )

            if method_data.trampoline_cpp_code and not is_virtual:
                raise ValueError(
                    f"{cdata.cls_key}::{method_name}: cannot specify trampoline_cpp_code for a non-virtual method"
                )

            if method_data.virtual_xform and not is_virtual:
                raise ValueError(
                    f"{cdata.cls_key}::{method_name}: cannot specify virtual_xform for a non-virtual method"
                )

            # pybind11 doesn't support this, user must fix it
            if (
                method.ref_qualifier == "&&"
                and not method_data.ignore_py
                and not method_data.cpp_code
            ):
                raise ValueError(
                    f"{cdata.cls_key}::{method_name}: has && ref-qualifier which cannot be directly bound by pybind11, must specify cpp_code or ignore_py"
                )

    def _on_class_method_process_overload_only(
        self, state: AWClassBlockState, method: Method
    ):
        cdata = state.user_data

        method_name = self._get_fn_name(method)
        if not method_name:
            return

        self.gendata.get_function_data(
            method_name,
            method,
            cdata.cls_key,
            cdata.data,
            True,
        )

    def _is_copy_move_constructor(
        self, cctx: ClassContext, first_type_param: DecoratedType
    ) -> bool:
        if isinstance(first_type_param, Reference):
            t = first_type_param.ref_to
        elif isinstance(first_type_param, MoveReference):
            t = first_type_param.moveref_to
        else:
            return False

        if not isinstance(t, Type):
            return False

        last_seg = t.typename.segments[-1]
        if not isinstance(last_seg, NameSpecifier):
            return False

        if len(t.typename.segments) == 1:
            return last_seg.name == cctx.cpp_name
        else:
            # This isn't quite right, but probably rarely happens?
            param_name = _fmt_nameonly(t.typename)
            return param_name == cctx.full_cpp_name

    def on_class_friend(self, state: AWClassBlockState, friend: FriendDecl) -> None:
        pass

    def on_class_end(self, state: AWClassBlockState) -> None:
        # post-process the class data
        cdata = state.user_data
        ctx = cdata.ctx
        class_data = cdata.data

        # If there isn't already a constructor, add a default constructor
        # - was going to add a FunctionContext for it, but.. this is way easier
        ctx.add_default_constructor = (
            not ctx.has_constructor
            and not class_data.nodelete
            and not class_data.force_no_default_constructor
        )

        has_trampoline = (
            ctx.is_polymorphic
            and not state.class_decl.final
            and not class_data.force_no_trampoline
        )

        # process methods and fields
        if has_trampoline:
            state.access = "protected"
            methods = ctx.wrapped_protected_methods
            for m in cdata.defer_protected_methods:
                self._on_class_method(state, m, methods)

            props = ctx.protected_properties
            for f in cdata.defer_protected_fields:
                self._on_class_field(state, f, props)

            state.access = "private"
            unused = []
            for m in cdata.defer_private_virtual_methods:
                self._on_class_method(state, m, unused)

            self.hctx.classes_with_trampolines.append(ctx)

            tmpl = ""
            if cdata.template_argument_list:
                tmpl = f", {cdata.template_argument_list}"

            trampoline_cfg = f"rpygen::PyTrampolineCfg_{cdata.cls_cpp_identifier}<{cdata.template_argument_list}>"
            tname = f"rpygen::PyTrampoline_{cdata.cls_cpp_identifier}<typename {ctx.full_cpp_name}{tmpl}, typename {trampoline_cfg}>"
            tvar = f"{ctx.cpp_name}_Trampoline"

            ctx.trampoline = TrampolineData(
                full_cpp_name=tname,
                var=tvar,
                inline_code=class_data.trampoline_inline_code,
                tmpl_args=cdata.base_template_args,
                tmpl_params=cdata.base_template_params,
                methods_to_disable=cdata.methods_to_disable,
                virtual_methods=cdata.virtual_methods,
                protected_constructors=cdata.protected_constructors,
                non_virtual_protected_methods=cdata.non_virtual_protected_methods,
            )

        elif class_data.trampoline_inline_code is not None:
            raise ValueError(
                f"{cdata.cls_key} has trampoline_inline_code specified, but there is no trampoline!"
            )

        else:
            # still need to do minimal processing to add deferred functions
            # to the overload tracker, otherwise we won't handle it correctly
            for m in cdata.defer_protected_methods:
                self._on_class_method_process_overload_only(state, m)
            for m in cdata.defer_private_virtual_methods:
                self._on_class_method_process_overload_only(state, m)

        for m in cdata.defer_private_nonvirtual_methods:
            self._on_class_method_process_overload_only(state, m)

    #
    # Function/method processing
    #

    def _on_fn_or_method(
        self,
        fn: Function,
        data: FunctionData,
        fn_name: str,
        scope_var: str,
        internal: bool,
        overload_tracker: OverloadTracker,
    ) -> FunctionContext:
        # if cpp_code is specified, don't release the gil unless the user
        # specifically asks for it
        if data.no_release_gil is None:
            release_gil = data.cpp_code is None
        else:
            release_gil = not data.no_release_gil

        all_params: typing.List[ParamContext] = []
        filtered_params: typing.List[ParamContext] = []
        keepalives = []

        has_out_param = False

        # Use this if one of the parameter types don't quite match
        param_override = data.param_override
        fn_disable_none = data.disable_none

        # keep track of param name changes so we can automatically update
        # documentation
        param_remap: typing.Dict[str, str] = {}

        #
        # Process parameters
        #

        for i, p in enumerate(fn.parameters):
            p_name = p.name
            if not p_name:
                p_name = f"param{i}"

            po = param_override.get(p_name, _default_param_data)

            pctx = self._on_fn_param(
                p,
                p_name,
                fn_disable_none,
                po,
                param_remap,
            )

            all_params.append(pctx)
            if not po.ignore:
                filtered_params.append(pctx)

            if pctx.category == ParamCategory.OUT:
                has_out_param = True

        return_value_policy = _rvp_map[data.return_value_policy]

        # Set up the function's name
        if data.rename:
            # user preference wins, of course
            py_name = data.rename
        elif isinstance(fn, Method) and fn.constructor:
            py_name = "__init__"
        else:
            # Python exposed function name converted to camelcase
            py_name = self._make_py_name(
                fn_name, data, is_operator=fn.operator is not None
            )
            if not py_name[:2].isupper():
                py_name = f"{py_name[0].lower()}{py_name[1:]}"

            if data.internal or internal:
                py_name = f"_{py_name}"

        doc = self._process_doc(fn.doxygen, data, param_remap=param_remap)

        # Allow the user to override our auto-detected keepalives
        if data.keepalive is not None:
            keepalives = data.keepalive

        # Check for user errors
        if not self.report_only:
            if fn.template:
                if data.template_impls is None and not data.cpp_code:
                    raise ValueError(
                        f"{fn_name}: must specify template impls for function template"
                    )
            else:
                if data.template_impls is not None:
                    raise ValueError(
                        f"{fn_name}: cannot specify template_impls for non-template functions"
                    )

        #
        # fn_retval is needed for gensig, vcheck assertions
        # - gensig is not computable here
        #
        fn_retval: typing.Optional[str] = None
        if fn.return_type:
            fn_retval = fn.return_type.format()
            self._add_type_caster(fn.return_type)

        fctx = FunctionContext(
            cpp_name=fn_name,
            doc=doc,
            scope_var=scope_var,
            # transforms
            py_name=py_name,
            cpp_return_type=fn_retval,
            all_params=all_params,
            filtered_params=filtered_params,
            has_buffers=bool(data.buffers),
            keepalives=keepalives,
            return_value_policy=return_value_policy,
            # info
            # vararg=fn.vararg,
            # user settings
            ignore_pure=data.ignore_pure,
            ignore_py=data.ignore_py,
            cpp_code=data.cpp_code,
            trampoline_cpp_code=data.trampoline_cpp_code,
            ifdef=data.ifdef,
            ifndef=data.ifndef,
            release_gil=release_gil,
            template_impls=data.template_impls,
            virtual_xform=data.virtual_xform,
            is_overloaded=overload_tracker,
            _fn=fn,
        )

        # Generate a special lambda wrapper only when needed
        if not data.cpp_code and (has_out_param or fctx.has_buffers):
            self._on_fn_make_lambda(data, fctx)

        return fctx

    def _on_fn_param(
        self,
        p: Parameter,
        p_name: str,
        fn_disable_none: typing.Optional[bool],
        param_override: ParamData,
        param_remap: typing.Dict[str, str],
    ):
        ptype, p_pointer, p_reference, p_const = _count_and_unwrap(p.type)
        fundamental = isinstance(ptype, Type) and _is_fundamental(
            ptype.typename.segments[-1]
        )
        self._add_type_caster(ptype)

        # TODO: get rid of this, use const by default?
        if isinstance(ptype, Type) and ptype.const:
            ptype.const = False
            cpp_type_no_const = ptype.format()
            ptype.const = True
        else:
            cpp_type_no_const = ptype.format()

        cpp_type = cpp_type_no_const

        if p_pointer:
            call_name = p_name
        elif p_reference:
            call_name = f"std::forward<decltype({p_name})>({p_name})"
        else:
            call_name = f"std::move({p_name})"

        # This is different because call_name might get special treatment later
        virtual_call_name = call_name
        cpp_retname = orig_pname = p_name

        # TODO: this is precarious
        # - needs to override some things
        force_out = False
        default = None
        disable_none = fn_disable_none
        if param_override is not _default_param_data:
            force_out = param_override.force_out
            if param_override.name:
                p_name = param_override.name
            if param_override.x_type:
                cpp_type = param_override.x_type
                self._add_user_type_caster(cpp_type)
            if param_override.default:
                default = param_override.default
            if param_override.no_default:
                default = None
            if param_override.disable_none is not None:
                disable_none = param_override.disable_none

        py_pname = p_name
        if iskeyword(py_pname):
            py_pname = f"{py_pname}_"

        if orig_pname != py_pname:
            param_remap[orig_pname] = py_pname

        # Autodetect disable_none if not explicitly specified
        if disable_none is None:
            disable_none = cpp_type.startswith("std::function")

        if disable_none:
            py_arg = f'py::arg("{py_pname}").none(false)'
        else:
            py_arg = f'py::arg("{py_pname}")'

        #
        # Default parameter
        #

        # Do this after cpp_type is resolved but before it gets its const
        if not default and p.default and not param_override.no_default:
            default = tokfmt(p.default.tokens)

        if default:
            default = self._resolve_default(default, cpp_type, ptype)
            if not param_override.disable_type_caster_default_cast:
                default = self._add_default_arg_cast(default, ptype)
            if default:
                py_arg = f"{py_arg} = {default}"

        pcat = ParamCategory.IN

        if force_out or (
            (p_pointer or p_reference == 1) and not p_const and fundamental
        ):
            if p_pointer:
                call_name = f"&{call_name}"
            else:
                call_name = p_name

            pcat = ParamCategory.OUT
        elif isinstance(ptype, Array):
            asz = param_override.array_size
            if not asz:
                asz = _fmt_array_size(ptype)

            if asz is not None:
                cpp_type = f"std::array<{ptype.array_of.format()}, {asz}>"
                call_name = f"{call_name}.data()"
                if not default:
                    default = "{}"
                self._add_user_type_caster("std::array")
            else:
                # it's a vector
                pass
            pcat = ParamCategory.OUT

        if p_const:
            cpp_type = f"const {cpp_type}"

        # TODO: this is weird, why aren't we using .format() here
        x_type_full = cpp_type
        x_type_full += "&" * p_reference
        x_type_full += "*" * p_pointer

        return ParamContext(
            arg_name=p_name,
            cpp_type=cpp_type,
            full_cpp_type=x_type_full,
            py_arg=py_arg,
            default=default,
            # only used by genlambda
            call_name=call_name,
            # only used if virtual, duh
            virtual_call_name=virtual_call_name,
            cpp_retname=cpp_retname,
            category=pcat,
        )

    def _on_fn_make_lambda(self, data: FunctionData, fctx: FunctionContext):
        """
        When we need to transform the C++ function to make it more pythonic, we
        autogenerate a lambda function as part of the wrapper. This is needed:

        * When an 'out' parameter is detected (a pointer receiving a value)
        * When a buffer + size parameter exists (either in or out)
        """

        # Statements to insert before calling the function
        lambda_pre: typing.List[str] = []

        # If buffer overrides present, apply those to the parameters
        if data.buffers:
            self._apply_buffer_params(data, fctx, lambda_pre)

        in_params: typing.List[ParamContext] = []
        out_params: typing.List[ParamContext] = []
        ret_params: typing.List[typing.Union[_ReturnParamContext, ParamContext]] = []
        tmp_params: typing.List[ParamContext] = []

        #
        # Sort the parameters
        #

        for pctx in fctx.filtered_params:
            if pctx.category == ParamCategory.OUT:
                out_params.append(pctx)
                tmp_params.append(pctx)

            elif pctx.category == ParamCategory.IN:
                in_params.append(pctx)

            elif pctx.category == ParamCategory.TMP:
                tmp_params.append(pctx)

        call_start = ""
        lambda_ret = ""

        # Return values (original return value + any out parameters)
        fn_retval = fctx.cpp_return_type
        if fn_retval and fn_retval != "void":
            call_start = "auto __ret ="
            ret_params = [_ReturnParamContext(cpp_retname="__ret", cpp_type=fn_retval)]
            ret_params.extend(out_params)
        else:
            ret_params.extend(out_params)

        if len(ret_params) == 1 and ret_params[0].cpp_type != "void":
            lambda_ret = f"return {ret_params[0].cpp_retname};"
        elif len(ret_params) > 1:
            t = ",".join([p.cpp_retname for p in ret_params])
            lambda_ret = f"return std::make_tuple({t});"

        # Temporary values to store out parameters in
        if tmp_params:
            for out in reversed(tmp_params):
                odef = out.default
                if not odef:
                    lambda_pre.insert(0, f"{out.cpp_type} {out.arg_name}")
                elif odef.startswith("{"):
                    lambda_pre.insert(0, f"{out.cpp_type} {out.arg_name}{odef}")
                else:
                    lambda_pre.insert(0, f"{out.cpp_type} {out.arg_name} = {odef}")

        pre = _lambda_predent + f";\n{_lambda_predent}".join(lambda_pre) + ";"

        fctx.genlambda = GeneratedLambda(
            pre=pre,
            call_start=call_start,
            ret=lambda_ret,
            in_params=in_params,
            out_params=out_params,
        )

    def _apply_buffer_params(
        self,
        data: FunctionData,
        fctx: FunctionContext,
        lambda_pre: typing.List[str],
    ):
        """
        Modifies the function parameters for buffer usage
        """

        # buffers: accepts a python object that supports the buffer protocol
        #          as input. If the buffer is an 'out' buffer, then it
        #          will request a writeable buffer. Data is written by the
        #          wrapped function to that buffer directly, and the length
        #          written (if the length is a pointer) will be returned
        buffer_params: typing.Dict[str, BufferData] = {}
        buflen_params: typing.Dict[str, bool] = {}

        for bufinfo in data.buffers:
            if bufinfo.src in buffer_params:
                raise ValueError(
                    f"buffer src({bufinfo.src}) is in multiple buffer specifications"
                )
            # length can be shared
            # elif bufinfo.len in buflen_params:
            #     raise ValueError(
            #         f"buffer len({bufinfo.len}) is in multiple buffer specifications"
            #     )
            buffer_params[bufinfo.src] = bufinfo
            buflen_params[bufinfo.len] = False

        dups = set(buffer_params.keys()).intersection(buflen_params.keys())
        if dups:
            names = "', '".join(dups)
            raise ValueError(f"These params are both buffer src and len: '{names}'")

        for pctx in fctx.all_params:
            p_name = pctx.arg_name
            if p_name in buffer_params:
                bufinfo = buffer_params.pop(p_name)
                bname = f"__{bufinfo.src}"

                pctx.call_name = f"({pctx.cpp_type}*){bname}.ptr"
                pctx.cpp_type = "const py::buffer"
                pctx.full_cpp_type = "const py::buffer&"

                # this doesn't seem to be true for bytearrays, which is silly
                # x_lambda_pre.append(
                #     f'if (PyBuffer_IsContiguous((Py_buffer*){p_name}.ptr(), \'C\') == 0) throw py::value_error("{p_name}: buffer must be contiguous")'
                # )

                # TODO: check for dimensions, strides, other dangerous things

                # bufinfo was validated and converted before it got here
                pctx.category = ParamCategory.IN
                if bufinfo.type is BufferType.IN:
                    lambda_pre += [f"auto {bname} = {p_name}.request(false)"]
                else:
                    lambda_pre += [f"auto {bname} = {p_name}.request(true)"]

                lambda_pre += [f"{bufinfo.len} = {bname}.size * {bname}.itemsize"]

                if bufinfo.minsz:
                    lambda_pre.append(
                        f'if ({bufinfo.len} < {bufinfo.minsz}) throw py::value_error("{p_name}: minimum buffer size is {bufinfo.minsz}")'
                    )

            elif p_name in buflen_params:
                buflen_params[p_name] = True

                # If the length is a pointer, assume that the function will accept
                # an incoming length, and set the outgoing length
                if pctx.full_cpp_type.endswith("*"):
                    pctx.call_name = f"&{p_name}"
                    pctx.category = ParamCategory.OUT
                else:
                    # if it's not a pointer, then the called function
                    # can't communicate through it, so ignore the parameter
                    pctx.call_name = p_name
                    pctx.category = ParamCategory.TMP

        if buffer_params:
            names = "', '".join(buffer_params.keys())
            raise ValueError(f"incorrect buffer param names '{names}'")

        unused_buflen_params = [k for k, v in buflen_params.items() if not v]
        if unused_buflen_params:
            names = "', '".join(unused_buflen_params)
            raise ValueError(f"incorrect buffer length names '{names}'")

    #
    # Utility methods
    #

    def _get_fn_name(self, fn: Function) -> typing.Optional[str]:
        s = fn.name.segments[-1]
        if isinstance(s, NameSpecifier):
            return s.name

        # name is too complicated (can this happen? should be a warning?)
        assert False
        return None

    def _get_module_var(self, data: HasSubpackage) -> str:
        if data.subpackage:
            var = f"pkg_{data.subpackage.replace('.', '_')}"
            self.hctx.subpackages[data.subpackage] = var
            return var

        return "m"

    def _make_py_name(
        self,
        name: str,
        data: HasNameData,
        strip_prefixes: typing.Optional[typing.List[str]] = None,
        is_operator: bool = False,
    ):
        if data.rename:
            return data.rename

        if strip_prefixes is None:
            strip_prefixes = self.user_cfg.strip_prefixes

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
            if not self.report_only:
                raise ValueError(f"name {name!r} is not a valid identifier")

        return name

    def _process_doc(
        self,
        doxygen: typing.Optional[str],
        data: HasDoc,
        append_prefix: str = "",
        param_remap: typing.Dict[str, str] = {},
    ) -> Documentation:
        doc = ""

        if data.doc is not None:
            doc = data.doc
        elif doxygen:
            doc = doxygen
            if param_remap:
                d = sphinxify.Doc.from_comment(doc)
                for param in d.params:
                    new_name = param_remap.get(param.name)
                    if new_name:
                        param.name = new_name
                doc = str(d)
            else:
                doc = sphinxify.process_raw(doc)

        if data.doc_append is not None:
            doc += f"\n{append_prefix}" + data.doc_append.replace(
                "\n", f"\n{append_prefix}"
            )

        return self._quote_doc(doc)

    def _quote_doc(self, doc: typing.Optional[str]) -> Documentation:
        doc_quoted: Documentation = None
        if doc:
            # TODO
            doc = doc.replace("\\", "\\\\").replace('"', '\\"')
            doc_quoted = doc.splitlines(keepends=True)
            doc_quoted = ['"%s"' % (dq.replace("\n", "\\n"),) for dq in doc_quoted]

        return doc_quoted

    def _extract_typealias(
        self,
        in_ta: typing.List[str],
        out_ta: typing.List[str],
        ta_names: typing.Set[str],
    ):
        for typealias in in_ta:
            if typealias.startswith("template"):
                out_ta.append(typealias)
            else:
                teq = typealias.find("=")
                if teq != -1:
                    ta_name = typealias[:teq].strip()
                    out_ta.append(f"using {typealias}")
                else:
                    ta_name = typealias.split("::")[-1]
                    out_ta.append(f"using {ta_name} = {typealias}")
                ta_names.add(ta_name)

    def _resolve_default(
        self,
        name: str,
        cpp_type: str,
        ptype: typing.Union[Array, FunctionType, Type],
    ) -> str:
        if name.isnumeric() or name in ("NULL", "nullptr"):
            pass
        elif name[0] == "{" and name[-1] == "}":
            if isinstance(ptype, Array):
                return name
            return f"{cpp_type}{name}"

        # if there's a parent, look there
        # -> this seems rather expensive for little reward, how often do we need
        #    this? Also, doesn't have any test coverage yet, so let's not do it
        #    for now
        #
        # parent = fn["parent"]
        # if parent:
        #     for prop in parent["properties"]["public"]:
        #         if prop["name"] == name:
        #             name = f"{parent['namespace']}::{parent['name']}::{name}"

        return name

    def _add_default_arg_cast(
        self, name: str, ptype: typing.Union[Array, FunctionType, Type]
    ) -> str:
        # Adds an explicit cast to a default arg for certain types that have
        # a type caster with an explicit default
        ntype: typing.Union[Array, FunctionType, Pointer, Type] = ptype
        while isinstance(ntype, Array):
            ntype = ntype.array_of
        if isinstance(ntype, Type):
            typename = _fmt_nameonly(ntype.typename)
            if typename:
                ccfg = self.casters.get(typename)
                if ccfg and ccfg.get("darg"):
                    found_typename = ccfg["typename"]
                    name = f"({found_typename}){name}"

        return name

    #
    # type caster utilities
    #

    def _add_type_caster(self, t: typing.Union[DecoratedType, FunctionType]):
        # pick apart the type and add each to the list of types
        # - it would be nice if we could just add this to a set
        #   and process it later, but that would probably be just
        #   as much work?
        while True:
            if isinstance(t, Type):
                self._add_type_caster_pqname(t.typename)
                return

            elif isinstance(t, FunctionType):
                self._add_type_caster(t.return_type)
                for p in t.parameters:
                    self._add_type_caster(p.type)
                return

            elif isinstance(t, Pointer):
                t = t.ptr_to
            elif isinstance(t, Reference):
                t = t.ref_to
            elif isinstance(t, MoveReference):
                t = t.moveref_to
            elif isinstance(t, Array):
                t = t.array_of
            else:
                assert False

    def _add_type_caster_pqname(self, typename: PQName):
        parts = []
        for p in typename.segments:
            if not isinstance(p, NameSpecifier):
                return
            parts.append(p.name)
            if p.specialization:
                for a in p.specialization.args:
                    if not isinstance(a.arg, Value):
                        self._add_type_caster(a.arg)

        self.types.add("::".join(parts))

    def _add_user_type_caster(self, typename: str):
        # defer until the end since there's lots of duplication
        self.user_types.add(typename)

    def _process_user_type_casters(self):
        # processes each user type caster and adds it to the processed list
        types = self.types
        for typename in self.user_types:
            tmpl_idx = typename.find("<")
            if tmpl_idx == -1:
                types.add(typename)
            else:
                types.add(typename[:tmpl_idx])
                types.update(
                    _type_caster_seps.split(typename[tmpl_idx:].replace(" ", ""))
                )

    def _set_type_caster_includes(self):
        # process user casters
        self._process_user_type_casters()
        casters = self.casters

        # identify any associated headers
        includes = set()
        for typename in self.types:
            ccfg = casters.get(typename)
            if ccfg:
                includes.add(ccfg["hdr"])

        self.hctx.type_caster_includes = sorted(includes)


def parse_header(
    name: str,
    header_path: pathlib.Path,
    header_root: pathlib.Path,
    gendata: GeneratorData,
    parser_options: ParserOptions,
    casters: typing.Dict[str, typing.Dict[str, typing.Any]],
    report_only: bool,
) -> HeaderContext:
    user_cfg = gendata.data

    # Initialize the header context with user configuration
    hctx = HeaderContext(
        hname=name,
        extra_includes_first=user_cfg.extra_includes_first,
        extra_includes=user_cfg.extra_includes,
        inline_code=user_cfg.inline_code,
        trampoline_signature=trampoline_signature,
        using_signature=_using_signature,
        rel_fname=str(header_path.relative_to(header_root)),
    )

    # Parse the header using a custom visitor
    visitor = AutowrapVisitor(hctx, gendata, casters, report_only)
    parser = CxxParser(
        str(header_path), None, visitor, parser_options, encoding=user_cfg.encoding
    )
    parser.parse()

    #
    # Per-header user specified data
    #

    for i, (k, tmpl_data) in enumerate(user_cfg.templates.items()):
        qualname = tmpl_data.qualname
        if "::" not in qualname:
            qualname = f"::{qualname}"
        qualname = qualname.translate(_qualname_trans)

        doc_add = tmpl_data.doc_append
        if doc_add:
            doc_add = f"\n{doc_add}"

        tctx = TemplateInstanceContext(
            scope_var=visitor._get_module_var(tmpl_data),
            var_name=f"tmplCls{i}",
            py_name=k,
            full_cpp_name_identifier=qualname,
            binder_typename=f"bind_{qualname}_{i}",
            params=tmpl_data.params,
            header_name=f"{qualname}.hpp",
            doc_set=visitor._quote_doc(tmpl_data.doc),
            doc_add=visitor._quote_doc(doc_add),
        )
        hctx.template_instances.append(tctx)

        # Ensure that template instances are created in class order if the
        # template class is in this header file
        # - not matching here is not an error
        qualname_match = tmpl_data.qualname.lstrip(":")
        for cctx in hctx.classes:
            if cctx.dep_cpp_name.lstrip(":") == qualname_match:
                assert cctx.template
                tctx.matched = True
                cctx.template.instances.append(tctx)
                break

        for param in tmpl_data.params:
            visitor._add_user_type_caster(param)

    # User typealias additions
    visitor._extract_typealias(user_cfg.typealias, hctx.user_typealias, set())

    # Type caster
    visitor._set_type_caster_includes()

    return hctx
