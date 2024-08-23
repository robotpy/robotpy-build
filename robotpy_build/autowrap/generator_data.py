import yaml

from ..config.autowrap_yml import (
    ClassData,
    EnumData,
    AutowrapConfigYaml,
    PropData,
    FunctionData,
)
from .j2_context import OverloadTracker

from cxxheaderparser.types import Function

import dataclasses
from typing import Dict, List, Optional, Tuple


@dataclasses.dataclass
class FnReportData:
    missing: bool = False
    overloads: Dict[str, bool] = dataclasses.field(default_factory=dict)
    tracker: OverloadTracker = dataclasses.field(default_factory=OverloadTracker)

    # need to be put into overloads if reports are being made
    deferred_signatures: List[Tuple[Function, bool]] = dataclasses.field(
        default_factory=list
    )


AttrMissingData = Dict[str, bool]
EnumMissingData = Dict[str, bool]
FnMissingData = Dict[str, FnReportData]


@dataclasses.dataclass
class ClsReportData:
    missing: bool
    attributes: AttrMissingData = dataclasses.field(default_factory=dict)
    enums: EnumMissingData = dataclasses.field(default_factory=dict)
    functions: FnMissingData = dataclasses.field(default_factory=dict)


class GeneratorData:
    """
    Used by the hooks to retrieve user-specified generation data, and
    report to the user that there is data missing
    """

    data: AutowrapConfigYaml

    def __init__(self, data: AutowrapConfigYaml):
        self.data = data

        default_ignore = self.data.defaults.ignore
        self._default_enum_data = EnumData(ignore=default_ignore)
        self._default_fn_data = FunctionData(ignore=default_ignore)
        self._default_method_data = FunctionData()
        self._default_class_data = ClassData(ignore=default_ignore)
        self._default_class_enum_data = EnumData()

        # report data
        self.functions: FnMissingData = {}
        self.classes: Dict[str, ClsReportData] = {}
        self.enums: EnumMissingData = {}
        self.attributes: AttrMissingData = {}

    def get_class_data(self, name: str) -> ClassData:
        """
        The 'name' is [parent_class::]class_name
        """
        data = self.data.classes.get(name)
        missing = data is None
        if missing:
            data = self._default_class_data

        self.classes[name] = ClsReportData(missing=missing)
        return data

    def get_cls_enum_data(
        self, name: str, cls_key: str, cls_data: ClassData
    ) -> EnumData:
        if name is None:
            # TODO
            return self._default_class_enum_data
        data = cls_data.enums.get(name)
        if data is None:
            self.classes[cls_key].enums[name] = False
            data = self._default_class_enum_data

        return data

    def get_enum_data(self, name: str) -> EnumData:
        data = self.data.enums.get(name)
        if data is None:
            self.enums[name] = False
            data = self._default_enum_data
        return data

    def get_function_data(
        self,
        name: str,
        fn: Function,
        cls_key: Optional[str] = None,
        cls_data: Optional[ClassData] = None,
        is_private: bool = False,
    ) -> Tuple[FunctionData, OverloadTracker]:
        if cls_data and cls_key:
            data = cls_data.methods.get(name)
            report_base = self.classes[cls_key].functions
        else:
            data = self.data.functions.get(name)
            report_base = self.functions

        report_data = report_base.get(name)
        if not report_data:
            report_data = FnReportData()
            report_base[name] = report_data

        missing = data is None
        report_data.missing = missing and not is_private

        # When retrieving function data, we have to take into account which overload
        # is being processed, so that the user can customize each overload uniquely
        # if desired

        # most functions don't have overloads, so instead of computing the
        # signature each time we defer it until we actually need to use it

        if missing:
            if cls_key:
                data = self._default_method_data
            else:
                data = self._default_fn_data
            report_data.deferred_signatures.append((fn, is_private))
        elif not data.overloads:
            report_data.deferred_signatures.append((fn, is_private))
        else:
            # When there is overload data present, we have to actually compute
            # the signature of every function
            signature = self._get_function_signature(fn)
            overload = data.overloads.get(signature)
            missing = overload is None
            if not missing and overload:
                # merge overload information
                data = data.dict(exclude_unset=True)
                del data["overloads"]
                data.update(overload.dict(exclude_unset=True))
                data = FunctionData(**data)
            report_data.overloads[signature] = is_private or not missing

        report_data.tracker.add_overload()
        return data, report_data.tracker

    def add_using_decl(
        self, name: str, cls_key: str, cls_data: ClassData, is_private: bool
    ):
        # copied from get_function_data
        data = cls_data.methods.get(name)
        report_base = self.classes[cls_key].functions

        report_data = report_base.get(name)
        if not report_data:
            report_data = FnReportData()
            report_base[name] = report_data

        missing = data is None
        report_data.missing = missing and not is_private

        # We count this as an overload because it might be
        report_data.tracker.add_overload()

    def get_cls_prop_data(
        self, name: str, cls_key: str, cls_data: ClassData
    ) -> PropData:
        data = cls_data.attributes.get(name)
        if data is None:
            self.classes[cls_key].attributes[name] = False
            data = PropData()

        return data

    def get_prop_data(self, name) -> PropData:
        data = self.data.attributes.get(name)
        if data is None:
            self.attributes[name] = False
            data = PropData()

        return data

    def report_missing(self, name: str, reporter: "MissingReporter"):
        """
        Generate a structure that can be copy/pasted into the generation
        data yaml and print it out if there's missing data
        """

        ignore_default = self.data.defaults.ignore
        report_missing = True
        if ignore_default and not self.data.defaults.report_ignored_missing:
            report_missing = False

        # note: sometimes we have strings from CppHeaderParser that aren't
        # strings, so we need to cast them to str so yaml doesn't complain

        data = self._process_missing(
            self.attributes,
            self.functions,
            self.enums,
            "functions",
            ignore_default,
            report_missing,
        )

        all_cls_data = {}
        for cls_key, cls_data in self.classes.items():
            if cls_data.missing and not report_missing:
                continue

            result = self._process_missing(
                cls_data.attributes,
                cls_data.functions,
                cls_data.enums,
                "methods",
                False,
                True,
            )
            if result or cls_data.missing:
                if ignore_default and cls_data.missing:
                    result["ignore"] = True
                all_cls_data[str(cls_key)] = result
        if all_cls_data:
            data["classes"] = all_cls_data

        if data:
            reporter.add_report(name, data)

        return data

    def _process_missing(
        self,
        attrs: AttrMissingData,
        fns: FnMissingData,
        enums: EnumMissingData,
        fn_key: str,
        ignore_default: bool,
        report_missing: bool,
    ):
        data: Dict[str, Dict[str, Dict]] = {}

        # attributes
        if attrs:
            for y in attrs.keys():
                assert isinstance(y, str)

            data["attributes"] = {str(n): {} for n in attrs.keys()}

        # enums
        if enums:
            enums_report = {}
            for en, enum_present in enums.items():
                if not enum_present and not report_missing:
                    continue
                enums_report[en] = {}
                if ignore_default:
                    enums_report[en]["ignore"] = True
            if enums_report:
                data["enums"] = enums_report

        # functions
        fn_report = {}
        for fn, fndata in fns.items():
            if fndata.missing and not report_missing:
                continue

            fn = str(fn)
            overloads = fndata.overloads
            deferred_signatures = fndata.deferred_signatures
            overloads_count = len(overloads) + len(deferred_signatures)
            if overloads_count > 1:
                # process each deferred signature
                for dfn, v in deferred_signatures:
                    signature = self._get_function_signature(dfn)
                    overloads[signature] = v

                has_data = all(overloads.values())
            else:
                has_data = not fndata.missing

            if not has_data:
                d = {}
                if fn == "swap":
                    d = {"ignore": True}

                if overloads_count > 1:
                    fn_report[fn] = {
                        "overloads": {
                            k: dict(**d) for k, v in overloads.items() if not v
                        }
                    }

                    for k, v in fn_report[fn]["overloads"].items():
                        if "initializer_list" in k:
                            v["ignore"] = True
                        if ignore_default:
                            v["ignore"] = True
                else:
                    fn_report[fn] = d
                    if ignore_default:
                        d["ignore"] = True
        if fn_report:
            data[fn_key] = fn_report

        return data

    def _get_function_signature(self, fn: Function) -> str:
        """
        Only includes the names of parameters and a [const] indicator if needed
        """

        signature = ", ".join(
            f"{p.type.format()}..." if p.param_pack else p.type.format()
            for p in fn.parameters
        )

        if getattr(fn, "const", False):
            if signature:
                signature = f"{signature} [const]"
            else:
                signature = "[const]"
        elif fn.constexpr:
            if signature:
                signature = f"{signature} [constexpr]"
            else:
                signature = "[constexpr]"

        return signature


class MissingReporter:
    def __init__(self):
        self.reports = {}

    def _merge(self, src, dst):
        for k, v in src.items():
            if isinstance(v, dict):
                if k not in dst:
                    dst[k] = v
                else:
                    self._merge(v, dst[k])
            else:
                dst[k] = v

    def add_report(self, name, data):
        if name in self.reports:
            self._merge(data, self.reports[name])
        else:
            self.reports[name] = data

    def as_yaml(self):
        for name, report in self.reports.items():
            yield name, (
                yaml.safe_dump(report, sort_keys=False)
                .replace(" {}", "")
                .replace("? ''\n          :", '"":')
                .replace("? ''\n      :", '"":')
            )
