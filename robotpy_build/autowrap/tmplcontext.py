from dataclasses import dataclass, field
from robotpy_build.config.autowrap_yml import ClassData
import typing

# only put in data that should be written out, don't store anything else
# to get rid of the immense amount of logic in the templates

# TODO: how is qualname determined?
# -> ns + decl_name
# -> class in class_data

Documentation = typing.Optional[typing.List[str]]


@dataclass
class EnumeratorContext:

    #: Name in C++
    cpp_name: str

    #: Name in python
    py_name: str

    #: Documentation
    doc: Documentation


@dataclass
class EnumContext:

    #: Name of variable in initializer
    varname: str

    #: Name of variable in initializer that this will attach to
    scope_var: str

    #: C++ name, including namespace/classname
    full_cpp_name: str

    #: Python name
    py_name: str

    #: Enum values
    values: typing.List[EnumeratorContext]

    #: Documentation
    doc: Documentation


@dataclass
class FieldContext:

    # needed for arrays and references -- underlying type including cv qualifiers,
    # but not including array reference
    cpp_type: str

    #: Name in C++
    cpp_name: str

    #: Name in python
    py_name: str

    readonly: bool
    static: bool

    reference: bool

    #: If an array, the underlying array size
    array_size: typing.Optional[str]

    #: Documentation
    doc: Documentation


@dataclass
class ParamContext:
    name: str

    # callname
    # retname
    # x_pyarg
    # default
    # - this is resolved from the parent sometimes, why

    # x_decl
    # - used in trampoline function definitions
    # - used in lambda generation
    # - used in py::init lambda generation

    # x_type_full
    # - used to generate signature for overload
    # - used to generate xdecl
    # - used to generate signature for py::init

    # x_type only used to generate x_type_full

    #: Documentation
    doc: Documentation


@dataclass
class FunctionContext:

    #: Name of variable in initializer that this will attach to
    scope_var: str

    pass

    # ... all the logic needs to be moved out of the template and
    #     inserted in the processing instead

    # data.template_impls
    # data. ifdef/ifndef
    # data.no_release_gil

    # used by globals too

    #

    # x_module_var?

    # x_in params
    # x_out params
    # x_all_params

    # x_genlambda

    # x_keepalives

    # return value policy

    # trampoline_qualname stuff from parent

    # operator

    # data.cpp_code

    # overloaded

    # fnptr::::
    #
    # cpp_code, qualname, fn.namespace
    # name, tmpl
    #
    # generates a lambda:
    # - cls_qualname
    # - in_params.x_decl

    # pre stmts
    # callstart
    # parameters.x_callname
    # post stmts

    # virtual_xform

    #: Documentation
    doc: Documentation


@dataclass
class BaseClassContext:
    pass

    # trampoline:
    # x_qualname_
    # x_params

    # . these are per-class
    # x_pybase_args
    # x_pybase_params

    # class


@dataclass
class TrampolineContext:
    pass

    # list of public + protected_if_final

    # list of inherits

    # cls namespace

    # header.using_values

    # base x_params

    # x_template_parameter_list

    # cls.pybase_args
    # cls.x_qualname_

    # cls.typealias

    # cls.constants

    # cls.name

    # public, protected, virtual?
    # - per-function data
    #   ignore_pure
    #   virtual_xform
    #   return type, x_name, name, parameters(.name)

    # same with protected
    # using_signature() -- why not in j2 as macro
    # trampoline_signature()

    # same with fields


# template data
# - cls.namespace
#
# - header.using_values
#
# x_template_parameter_list
#
# cls.x_qualname_
#
# cls_init
# cls_def
#
# data.template_inline_code


@dataclass
class ClassContext:

    # used for dealing with methods/etc
    ignored: bool
    cls_key: str
    data: ClassData
    has_trampoline: bool
    final: bool

    full_cpp_name: str

    #: Name of variable in initializer that this will attach to
    scope_var: str

    #: Name of variable in initializer for this class
    varname: str

    # cls_using
    # - typealias
    # - constants

    #: Documentation
    doc: Documentation

    bases: typing.List[BaseClassData]

    # header:

    # extra_includes/extra_includes_first

    trampoline: typing.Optional[TrampolineData]

    # add default constructor
    # {% if not cls.x_has_constructor and not cls.data.nodelete and not cls.data.force_no_default_constructor %}

    # template_params
    #

    # don't add protected things if trampoline not enabled
    # .. more nuance than that

    classes: typing.List["ClassContext"] = field(default_factory=list)

    enums: typing.List[EnumContext] = field(default_factory=list)

    anon_enums: typing.List[EnumContext] = field(default_factory=list)


@dataclass
class PackageContext:

    #: If a subpackage, this is set
    name: str

    enums: typing.List[EnumContext] = field(default_factory=list)

    # classes

    # trampolines

    # template_classes


@dataclass
class HeaderContext:
    #
    rel_fname: str

    # classes

    # trampolines

    # template_classes

    using_ns: typing.List[str] = field(default_factory=list)

    # subpackages??? or how is this different
    packages: typing.Dict[str, PackageContext] = field(default_factory=dict)


# get rid of .ignore

# per-header data
# .. rel_fname, mod_fn
# .. global using != typealias
# .. has_operators
#
# .. templates, type_caster_includes
#
# per-class data
#
#
# classes, class enums, class methods, global methods
#

# attrs are faster in jinja, so use that


# header
# - classes
#   - fns
#   - enums
#   - vars
# - enums
# - vars
# - fns
#
# class
# - trampoline
# - templates
#   .. needs per-header using, per-class using

#
# class_hierarchy: is this still needed after two-phase?
#
