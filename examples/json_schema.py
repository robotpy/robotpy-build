#!/usr/bin/env python
import json
import sys

from robotpy_build.config.autowrap_yml import AutowrapConfigYaml

schema = AutowrapConfigYaml.schema()
nullable_types = (
    "PropData",
    "ClassData",
    "EnumData",
    "FunctionData",
)

for name, definition in schema["definitions"].items():
    if (
        name in nullable_types
        and definition["type"] == "object"
        and "default" not in definition
    ):
        definition["type"] = ["object", "null"]

json.dump(schema, sys.stdout, indent="\t")
