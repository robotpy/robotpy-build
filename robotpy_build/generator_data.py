import yaml

from .hooks_datacfg import (
    ClassData,
    EnumData,
    HooksDataYaml,
    PropData,
    FunctionData,
)

from typing import Dict, Optional


class GeneratorData:
    """
    Used by the hooks to retrieve user-specified generation data, and
    report to the user that there is data missing
    """

    data: HooksDataYaml

    def __init__(self, data: HooksDataYaml):
        self.data = data

        # report data
        self.functions: Dict[str, bool] = {}
        self.classes: Dict[str, Dict] = {}
        self.enums: Dict[str, bool] = {}
        self.attributes: Dict[str, bool] = {}

    def get_class_data(self, name: str) -> ClassData:
        data = self.data.classes.get(name)
        missing = data is None
        if missing:
            data = ClassData()

        self.classes[name] = {
            "attributes": {},
            "enums": {},
            "functions": {},
            "missing": missing,
        }
        return data

    def get_cls_enum_data(
        self, name: str, cls_key: str, cls_data: ClassData
    ) -> EnumData:
        if name is None:
            # TODO
            return EnumData()
        data = cls_data.enums.get(name)
        if data is None:
            self.classes[cls_key]["enums"][name] = False
            data = EnumData()

        return data

    def get_enum_data(self, name: str) -> EnumData:
        data = self.data.enums.get(name)
        if data is None:
            self.enums[name] = False
            data = EnumData()
        return data

    def get_function_data(
        self,
        fn: dict,
        signature: str,
        cls_key: Optional[str] = None,
        cls_data: Optional[ClassData] = None,
        is_private: bool = False,
    ) -> FunctionData:
        name = fn["name"]
        if cls_data and cls_key:
            data = cls_data.methods.get(name)
            report_base = self.classes[cls_key]["functions"]
        else:
            data = self.data.functions.get(name)
            report_base = self.functions

        report_base = report_base.setdefault(name, {"overloads": {}, "first": fn})
        missing = data is None
        report_base["missing"] = missing and not is_private

        if missing:
            data = FunctionData()
        else:
            overload = data.overloads.get(signature)
            missing = overload is None
            if not missing and overload:
                # merge overload information
                data = data.dict(exclude_unset=True)
                del data["overloads"]
                data.update(overload.dict(exclude_unset=True))
                data = FunctionData(**data)

        report_base["overloads"][signature] = is_private or not missing

        # TODO: doesn't belong here
        is_overloaded = len(report_base["overloads"]) > 1
        if is_overloaded:
            report_base["first"]["x_overloaded"] = True
        fn["x_overloaded"] = is_overloaded

        return data

    def get_cls_prop_data(
        self, name: str, cls_key: str, cls_data: ClassData
    ) -> PropData:
        data = cls_data.attributes.get(name)
        if data is None:
            self.classes[cls_key]["attributes"][name] = False
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

        # note: sometimes we have strings from CppHeaderParser that aren't
        # strings, so we need to cast them to str so yaml doesn't complain

        data = self._process_missing(
            self.attributes, self.functions, self.enums, "functions"
        )

        all_cls_data = {}
        for cls_key, cls_data in self.classes.items():
            result = self._process_missing(
                cls_data["attributes"],
                cls_data["functions"],
                cls_data["enums"],
                "methods",
            )
            if result or cls_data["missing"]:
                all_cls_data[str(cls_key)] = result
        if all_cls_data:
            data["classes"] = all_cls_data

        if data:
            reporter.add_report(name, data)

        return data

    def _process_missing(self, attrs, fns, enums, fn_key: str):

        data: Dict[str, Dict[str, Dict]] = {}

        # attributes
        if attrs:
            for y in attrs.keys():
                assert isinstance(y, str)

            data["attributes"] = {str(n): {} for n in attrs.keys()}

        # enums
        if enums:
            data["enums"] = {str(n): {} for n in enums.keys()}

        # functions
        fn_report = {}
        for fn, fndata in fns.items():
            fn = str(fn)
            overloads = fndata["overloads"]
            overloads_count = len(overloads)
            if overloads_count > 1:
                has_data = all(overloads.values())
            else:
                has_data = not fndata["missing"]

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
                else:
                    fn_report[fn] = d
        if fn_report:
            data[fn_key] = fn_report

        return data


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
