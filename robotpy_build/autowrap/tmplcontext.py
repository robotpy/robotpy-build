from dataclasses import dataclass
import typing

# only put in data that should be written out, don't store anything else
# to get rid of the immense amount of logic in the templates

# TODO: how is qualname determined?
# -> ns + decl_name
# -> class in class_data


@dataclass
class EnumContext:
    pass

    # x_namespace
    # name
    # doc
    # named vs unnamed

    # per-value: x_name, name, doc


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


@dataclass
class FunctionContext:
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


@dataclass
class VariableContext:
    pass

    # name
    # x_type

    # constant/constexpr/x_readonly
    # reference
    # array
    # array_size
    # x_name

    # x_doc


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

    #

    # cls_using
    # - typealias
    # - constants

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


@dataclass
class HeaderContext:
    #
    rel_fname: str


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
