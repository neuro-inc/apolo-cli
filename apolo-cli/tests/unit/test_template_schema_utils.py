from typing import Any, Dict

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from apolo_cli.template_schema_utils import (
    _generate_example_value,
    _generate_sample_from_schema,
    _generate_yaml_from_schema,
    _resolve_ref,
)


class TestResolveRef:
    def test_resolve_ref_simple(self) -> None:
        schema = {
            "definitions": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                }
            }
        }
        result = _resolve_ref(schema, "#/definitions/person", schema)
        assert result == {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

    def test_resolve_ref_nested(self) -> None:
        schema = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    }
                }
            }
        }
        result = _resolve_ref(schema, "#/components/schemas/User", schema)
        assert result == {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }

    def test_resolve_ref_invalid_path(self) -> None:
        schema: Dict[str, Any] = {"definitions": {}}
        result = _resolve_ref(schema, "#/definitions/nonexistent", schema)
        assert result == {}

    def test_resolve_ref_external(self) -> None:
        schema: Dict[str, Any] = {}
        result = _resolve_ref(schema, "http://example.com/schema", schema)
        assert result == {}


class TestGenerateExampleValue:
    def test_string_type(self) -> None:
        prop_schema = {"type": "string"}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == ""

    def test_string_with_enum(self) -> None:
        prop_schema = {"type": "string", "enum": ["value1", "value2", "value3"]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == "value1"

    def test_string_with_default(self) -> None:
        prop_schema = {"type": "string", "default": "default_value"}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == "default_value"

    def test_integer_type(self) -> None:
        prop_schema = {"type": "integer"}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == 0

    def test_integer_with_enum(self) -> None:
        prop_schema = {"type": "integer", "enum": [10, 20, 30]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == 10

    def test_integer_port_special_case(self) -> None:
        prop_schema = {"type": "integer"}
        result = _generate_example_value(prop_schema, "port")
        assert result == 8080

    def test_number_type(self) -> None:
        prop_schema = {"type": "number"}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == 0.0

    def test_boolean_type(self) -> None:
        prop_schema = {"type": "boolean"}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result is False

    def test_boolean_with_default(self) -> None:
        prop_schema = {"type": "boolean", "default": True}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result is True

    def test_array_type(self) -> None:
        prop_schema = {"type": "array", "items": {"type": "string"}}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == [""]

    def test_array_with_object_items(self) -> None:
        prop_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "integer"},
                },
            },
        }
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == [{"name": "", "value": 0}]

    def test_object_type(self) -> None:
        prop_schema = {
            "type": "object",
            "properties": {"field1": {"type": "string"}, "field2": {"type": "integer"}},
        }
        result = _generate_example_value(prop_schema, "test_prop")
        assert isinstance(result, CommentedMap)
        assert result == {"field1": "", "field2": 0}

    def test_object_with_nested_objects(self) -> None:
        prop_schema = {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {"inner": {"type": "string"}},
                }
            },
        }
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == {"outer": {"inner": ""}}

    def test_ref_resolution(self) -> None:
        root_schema = {
            "definitions": {"Name": {"type": "string", "description": "Person's name"}}
        }
        prop_schema = {"$ref": "#/definitions/Name"}
        result = _generate_example_value(prop_schema, "test_prop", root_schema)
        assert result == ""

    def test_ref_with_circular_reference(self) -> None:
        root_schema = {
            "definitions": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "next": {"$ref": "#/definitions/Node"},
                    },
                }
            }
        }
        prop_schema = {"$ref": "#/definitions/Node"}
        result = _generate_example_value(prop_schema, "test_prop", root_schema)
        assert result["value"] == ""
        assert result["next"] is None

    def test_anyof_with_null(self) -> None:
        prop_schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result is None

    def test_anyof_without_null(self) -> None:
        prop_schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == ""

    def test_anyof_all_null(self) -> None:
        prop_schema = {"anyOf": [{"type": "null"}]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result is None

    def test_anyof_with_ref(self) -> None:
        root_schema = {"definitions": {"Name": {"type": "string"}}}
        prop_schema = {"anyOf": [{"$ref": "#/definitions/Name"}, {"type": "null"}]}
        result = _generate_example_value(prop_schema, "test_prop", root_schema)
        assert result is None

    def test_oneof_with_null(self) -> None:
        prop_schema = {"oneOf": [{"type": "string"}, {"type": "null"}]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result is None

    def test_oneof_without_null(self) -> None:
        prop_schema = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == ""

    def test_allof(self) -> None:
        prop_schema = {
            "allOf": [
                {"type": "object", "properties": {"field1": {"type": "string"}}},
                {"properties": {"field2": {"type": "integer"}}},
            ]
        }
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == {"field1": ""}

    def test_allof_empty(self) -> None:
        prop_schema: Dict[str, Any] = {"allOf": []}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result is None

    def test_no_type_with_properties(self) -> None:
        prop_schema = {
            "properties": {"field1": {"type": "string"}, "field2": {"type": "integer"}}
        }
        result = _generate_example_value(prop_schema, "test_prop")
        # When no type is specified, it defaults to "string"
        assert result == ""

    def test_no_type_no_properties(self) -> None:
        prop_schema: Dict[str, Any] = {}
        result = _generate_example_value(prop_schema, "test_prop")
        assert result == ""

    def test_with_parent_map_and_description(self) -> None:
        parent_map = CommentedMap()
        prop_schema = {"type": "string", "description": "This is a test property"}
        result = _generate_example_value(
            prop_schema, "test_prop", None, parent_map, indent_level=2
        )
        assert result == ""

    def test_with_x_description(self) -> None:
        parent_map = CommentedMap()
        prop_schema = {"type": "string", "x-description": "This is an x-description"}
        result = _generate_example_value(
            prop_schema, "test_prop", None, parent_map, indent_level=2
        )
        assert result == ""


class TestGenerateSampleFromSchema:
    def test_object_schema(self) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
        result = _generate_sample_from_schema(schema)
        assert result == {"name": "", "age": 0}

    def test_schema_with_properties(self) -> None:
        schema = {
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "boolean"},
                "field3": {"type": "array", "items": {"type": "integer"}},
            }
        }
        result = _generate_sample_from_schema(schema)
        assert result == {"field1": "", "field2": False, "field3": [0]}

    def test_with_comments(self) -> None:
        schema = {
            "properties": {
                "field1": {"type": "string", "description": "Field 1 description"},
                "field2": {"type": "integer", "description": "Field 2 description"},
            }
        }
        result = _generate_sample_from_schema(schema, with_comments=True)
        assert isinstance(result, CommentedMap)
        assert result == {"field1": "", "field2": 0}

    def test_empty_schema(self) -> None:
        schema: Dict[str, Any] = {}
        result = _generate_sample_from_schema(schema)
        assert result == {}


class TestGenerateYamlFromSchema:
    def test_basic_schema(self) -> None:
        schema = {
            "properties": {
                "param1": {"type": "string", "default": "value1"},
                "param2": {"type": "integer"},
            }
        }
        result = _generate_yaml_from_schema(schema, "test-template", "1.0.0")

        assert "# Application template configuration for: test-template" in result
        assert "template_name: test-template" in result
        assert "template_version: 1.0.0" in result
        assert "param1: value1" in result
        assert "param2: 0" in result

    def test_complex_schema_with_nested_objects(self) -> None:
        schema = {
            "properties": {
                "database": {
                    "type": "object",
                    "description": "Database configuration",
                    "properties": {
                        "host": {"type": "string", "default": "localhost"},
                        "port": {"type": "integer"},
                        "credentials": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "password": {"type": "string"},
                            },
                        },
                    },
                }
            }
        }
        result = _generate_yaml_from_schema(schema, "db-app", "2.0.0")

        yaml_obj = YAML()
        parsed = yaml_obj.load(result)

        assert parsed["template_name"] == "db-app"
        assert parsed["template_version"] == "2.0.0"
        assert parsed["input"]["database"]["host"] == "localhost"
        assert parsed["input"]["database"]["port"] == 8080
        assert parsed["input"]["database"]["credentials"]["username"] == ""
        assert parsed["input"]["database"]["credentials"]["password"] == ""

    def test_schema_with_arrays(self) -> None:
        schema = {
            "properties": {
                "servers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "ip": {"type": "string"},
                        },
                    },
                }
            }
        }
        result = _generate_yaml_from_schema(schema, "server-list", "1.0.0")

        yaml_obj = YAML()
        parsed = yaml_obj.load(result)

        assert parsed["input"]["servers"] == [{"name": "", "ip": ""}]

    def test_empty_schema(self) -> None:
        schema: Dict[str, Any] = {}
        result = _generate_yaml_from_schema(schema, "empty-template", "1.0.0")

        assert "template_name: empty-template" in result
        assert "template_version: 1.0.0" in result
        assert "input: {}" in result

    def test_header_comments(self) -> None:
        schema = {"properties": {"param": {"type": "string"}}}
        result = _generate_yaml_from_schema(schema, "comment-test", "1.0.0")

        assert "# Application template configuration for: comment-test" in result
        assert "# Fill in the values below to configure your application." in result
        assert "# To use values from another app, use the following format:" in result
        assert "# my_param:" in result
        assert '#   type: "app-instance-ref"' in result
        assert '#   instance_id: "<app-instance-id>"' in result
        assert '#   param_name: "<param-name-from-other-app>"' in result
