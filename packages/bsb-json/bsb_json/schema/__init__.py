import json
import typing

from bsb.config import get_config_attributes


def get_json_schema(root):
    schema = get_schema(root)
    return json.dumps(schema)


def get_schema(root):
    defs = {}
    schema = object_schema(root, defs)
    schema["title"] = "Configuration"
    schema["description"] = "Automated JSON schema of configuration object"
    schema["$defs"] = defs
    return schema


def object_schema(obj, defs=None):
    # Import the scaffold object here to avoid circular imports when the JSON parser is
    # loaded.
    from bsb.core import Scaffold

    schema = {"type": "object", "properties": {}}
    cls = obj.__class__
    obj_hints = typing.get_type_hints(cls, localns={"Scaffold": Scaffold})
    obj_attrs = get_config_attributes(cls)
    for attr, _descr in obj_attrs.items():
        hint = obj_hints.get(attr, str)
        schema["properties"][attr] = attr_schema(hint, defs)

    return schema


def attr_schema(hint, defs=None):
    if defs is None:
        defs = {}
    schema = {}
    try:
        is_dict = issubclass(typing.get_origin(hint), dict)
        is_list = issubclass(typing.get_origin(hint), list)
    except TypeError:
        is_dict = False
        is_list = False
    if hint is str:
        schema["type"] = "string"
    elif hint is int:
        schema["type"] = "integer"
    elif hint is float:
        schema["type"] = "number"
    elif hint is bool:
        schema["type"] = "boolean"
    elif is_list:
        schema["type"] = "array"
        schema["items"] = attr_schema(typing.get_args(hint)[0], defs)
    elif is_dict:
        schema["type"] = "object"
        schema["properties"] = {}
        schema["additionalProperties"] = attr_schema(typing.get_args(hint)[1], defs)
    else:
        try:
            is_node = get_config_attributes(hint)
        except Exception:
            is_node = False
        if is_node:
            key = defs_key(hint)
            if key not in defs:
                defs[key] = object_schema(hint)
            return schema_def_ref(hint)
        else:
            schema["type"] = "object"
            schema["properties"] = {}
            schema["description"] = f"Could not determine schema of type {hint}"

    return schema


def defs_key(hint):
    return str(hint.__name__)


def schema_def_ref(hint):
    return {"$ref": f"#/$defs/{defs_key(hint)}"}
