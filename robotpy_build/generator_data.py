import sys
import yaml

from .hooks_datacfg import (
    ClassData,
    EnumData,
    HooksDataYaml,
    PropData,
    FunctionData,
)

from typing import Optional


_missing = object()


class GeneratorData:
    """
        Used by the hooks to retrieve user-specified generation data, and 
        report to the user that there is data missing
    """

    data: HooksDataYaml

    def __init__(self, data: HooksDataYaml):
        self.data = data

        # report data
        self.functions = {}
        self.classes = {}
        self.enums = {}
        self.attributes = {}

    def get_class_data(self, name: str) -> ClassData:
        data = self.data.classes.get(name, _missing)
        missing = data is _missing
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
        self, name: str, cls_name: str, cls_data: ClassData
    ) -> EnumData:
        if name is None:
            # TODO
            return EnumData()
        data = cls_data.enums.get(name, _missing)
        if data is _missing:
            self.classes[cls_name]["enums"][name] = False
            data = EnumData()

        return data

    def get_enum_data(self, name: str) -> EnumData:
        data = self.data.enums.get(name, _missing)
        if data is _missing:
            self.enums[name] = False
            data = EnumData()
        return data

    def get_function_data(
        self,
        fn: dict,
        signature: str,
        cls_name: Optional[str] = None,
        cls_data: Optional[ClassData] = None,
    ) -> FunctionData:
        name = fn["name"]
        if cls_data:
            data = cls_data.methods.get(name, _missing)
            report_base = self.classes[cls_name]["functions"]
        else:
            data = self.data.functions.get(name, _missing)
            report_base = self.functions

        report_base = report_base.setdefault(name, {"overloads": {}, "first": fn})
        missing = data is _missing
        report_base["missing"] = missing

        if missing:
            data = FunctionData()
        else:
            overload = data.overloads.get(signature, _missing)
            missing = overload is _missing
            if not missing and overload:
                # merge overload information
                data = data.dict(exclude_unset=True)
                del data["overloads"]
                data.update(overload.dict(exclude_unset=True))
                data = FunctionData(**data)

        report_base["overloads"][signature] = not missing

        # TODO: doesn't belong here
        is_overloaded = len(report_base["overloads"]) > 1
        if is_overloaded:
            report_base["first"]["x_overloaded"] = True
        fn["x_overloaded"] = is_overloaded

        return data

    def get_cls_prop_data(
        self, name: str, cls_name: str, cls_data: ClassData
    ) -> PropData:
        data = cls_data.attributes.get(name, _missing)
        if data is _missing:
            self.classes[cls_name]["attributes"][name] = False
            data = PropData()

        return data

    def get_prop_data(self, name) -> PropData:
        data = self.data.attributes.get(name, _missing)
        if data is _missing:
            self.attributes[name] = False
            data = PropData()

        return data

    def report_missing(self, name: str, fp=sys.stdout):
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
        for cls_name, cls_data in self.classes.items():
            result = self._process_missing(
                cls_data["attributes"],
                cls_data["functions"],
                cls_data["enums"],
                "methods",
            )
            if result or cls_data["missing"]:
                # show this first
                r = {"shared_ptr": True}
                r.update(result)
                all_cls_data[str(cls_name)] = r
        if all_cls_data:
            data["classes"] = all_cls_data

        if data:
            print("WARNING: some items not in generation yaml for", name)
            print(
                yaml.safe_dump(data, sort_keys=False)
                .replace(" {}", "")
                .replace("? ''\n          :", '"":'),
                file=fp,
            )

    def _process_missing(self, attrs, fns, enums, fn_key: str):

        data = {}

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
                if overloads_count > 1:
                    fn_report[fn] = {
                        "overloads": {k: {} for k, v in overloads.items() if not v}
                    }
                else:
                    fn_report[fn] = {}
        if fn_report:
            data[fn_key] = fn_report

        return data

