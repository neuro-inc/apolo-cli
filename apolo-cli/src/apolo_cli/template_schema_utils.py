import io
from typing import Any, Dict, Optional, Union

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


def _resolve_ref(
    schema: Dict[str, Any], ref: str, root_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Resolve a JSON Schema $ref reference."""
    if ref.startswith("#/"):
        # Internal reference
        path_parts = ref[2:].split("/")
        current = root_schema
        for part in path_parts:
            current = current.get(part, {})
        return current
    return {}


def _generate_example_value(
    prop_schema: Dict[str, Any],
    prop_name: str,
    root_schema: Optional[Dict[str, Any]] = None,
    parent_map: Optional[CommentedMap] = None,
    indent_level: int = 0,
    _visited_refs: Optional[set[str]] = None,
) -> Any:
    """Generate example values from JSON schema with comments."""
    if _visited_refs is None:
        _visited_refs = set()

    # Resolve the full schema first
    resolved_schema = prop_schema.copy()

    # Handle $ref references
    if "$ref" in prop_schema and "properties" not in prop_schema:
        ref = prop_schema["$ref"]
        # Check for circular reference
        if ref in _visited_refs:
            return None  # Return None for circular references

        if root_schema:
            _visited_refs.add(ref)
            ref_schema = _resolve_ref(prop_schema, ref, root_schema)
            # Don't update resolved_schema, instead process the ref_schema directly
            # but merge any descriptions from the original prop_schema
            for field in ["description", "x-description", "x-title", "title"]:
                if field in prop_schema and field not in ref_schema:
                    ref_schema[field] = prop_schema[field]
            result = _generate_example_value(
                ref_schema,
                prop_name,
                root_schema,
                parent_map,
                indent_level,
                _visited_refs,
            )
            _visited_refs.remove(ref)
            return result
        return ""

    # Handle anyOf/oneOf/allOf
    if "anyOf" in prop_schema:
        # Check if this is an optional field (contains null type)
        has_null = any(opt.get("type") == "null" for opt in prop_schema["anyOf"])
        non_null_options = [
            opt for opt in prop_schema["anyOf"] if opt.get("type") != "null"
        ]

        # For anyOf with $ref, resolve the ref first
        if non_null_options:
            for opt in non_null_options:
                if "$ref" in opt and root_schema:
                    resolved = _resolve_ref(opt, opt["$ref"], root_schema)
                    # Merge resolved schema properties for description
                    for field in ["description", "x-description"]:
                        if field in resolved and field not in resolved_schema:
                            resolved_schema[field] = resolved[field]

        # If optional (has null) and has non-null options
        if has_null and non_null_options:
            # For optional fields, return None
            value = None
        elif non_null_options:
            # For required fields, process the first non-null option
            value = _generate_example_value(
                non_null_options[0],
                prop_name,
                root_schema,
                None,
                indent_level,
                _visited_refs,
            )
        else:
            # If all options are null, return null
            value = None

        # Add comment if parent_map provided
        if parent_map is not None and prop_name:
            description = resolved_schema.get("description") or resolved_schema.get(
                "x-description"
            )
            if description:
                parent_map.yaml_set_comment_before_after_key(
                    prop_name, before=description, indent=indent_level
                )

        return value

    if "oneOf" in prop_schema:
        # Check if this is an optional field (contains null type)
        has_null = any(opt.get("type") == "null" for opt in prop_schema["oneOf"])
        non_null_options = [
            opt for opt in prop_schema["oneOf"] if opt.get("type") != "null"
        ]

        # If optional (has null) and has non-null options
        if has_null and non_null_options:
            # For optional fields, return None
            value = None
        elif non_null_options:
            # For required fields, process the first non-null option
            value = _generate_example_value(
                non_null_options[0],
                prop_name,
                root_schema,
                None,
                indent_level,
                _visited_refs,
            )
        else:
            # If all options are null, return null
            value = None

        # Add comment if parent_map provided
        if parent_map is not None and prop_name:
            description = resolved_schema.get("description") or resolved_schema.get(
                "x-description"
            )
            if description:
                parent_map.yaml_set_comment_before_after_key(
                    prop_name, before=description, indent=indent_level
                )

        return value

    if "allOf" in prop_schema:
        # Merge all schemas (simplified approach - just use first for now)
        if prop_schema["allOf"]:
            value = _generate_example_value(
                prop_schema["allOf"][0],
                prop_name,
                root_schema,
                None,
                indent_level,
                _visited_refs,
            )
        else:
            value = None

        # Add comment if parent_map provided
        if parent_map is not None and prop_name:
            description = resolved_schema.get("description") or resolved_schema.get(
                "x-description"
            )
            if description:
                parent_map.yaml_set_comment_before_after_key(
                    prop_name, before=description, indent=indent_level
                )

        return value

    prop_type = resolved_schema.get("type", "string")

    # Get description from resolved schema
    description = resolved_schema.get("description") or resolved_schema.get(
        "x-description"
    )

    # Generate the value
    if "default" in resolved_schema:
        value = resolved_schema["default"]
    elif prop_type == "object":
        # Create CommentedMap for nested objects
        result = CommentedMap()
        properties = resolved_schema.get("properties", {})
        for nested_prop_name, nested_prop_def in properties.items():
            result[nested_prop_name] = _generate_example_value(
                nested_prop_def,
                nested_prop_name,
                root_schema,
                result,
                indent_level + 2,
                _visited_refs,
            )
        value = result
    elif prop_type == "string":
        if "enum" in resolved_schema:
            value = resolved_schema["enum"][0]
        else:
            # For required strings, return empty string
            value = ""
    elif prop_type == "integer":
        if "enum" in resolved_schema:
            value = resolved_schema["enum"][0]
        elif prop_name.lower() in ["port"]:
            value = 8080
        else:
            value = 0
    elif prop_type == "number":
        value = 0.0
    elif prop_type == "boolean":
        value = False
    elif prop_type == "array":
        items_schema = resolved_schema.get("items", {})
        example_item = _generate_example_value(
            items_schema, "item", root_schema, None, indent_level, _visited_refs
        )
        value = [example_item]
    else:
        # If no type is specified but we have properties, treat it as an object
        if "properties" in resolved_schema:
            result = CommentedMap()
            for nested_prop_name, nested_prop_def in resolved_schema[
                "properties"
            ].items():
                result[nested_prop_name] = _generate_example_value(
                    nested_prop_def,
                    nested_prop_name,
                    root_schema,
                    result,
                    indent_level + 2,
                    _visited_refs,
                )
            value = result
        else:
            value = ""

    # Add comment to parent if provided
    if parent_map is not None and prop_name and description:
        parent_map.yaml_set_comment_before_after_key(
            prop_name, before=description, indent=indent_level
        )

    return value


def _generate_sample_from_schema(
    schema: Dict[str, Any], with_comments: bool = False, indent_level: int = 0
) -> Any:
    """Generate sample data from JSON schema, optionally with comments."""
    # If the schema itself defines an object type, process it directly
    if schema.get("type") == "object":
        return _generate_example_value(schema, "root", schema, None, indent_level)

    # Otherwise, process properties if they exist
    result: Union[CommentedMap, Dict[str, Any]]
    if with_comments:
        result = CommentedMap()
    else:
        result = {}

    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            result[prop_name] = _generate_example_value(
                prop_schema,
                prop_name,
                schema,
                result if with_comments and isinstance(result, CommentedMap) else None,
                indent_level,
            )

    return result


def _generate_yaml_from_schema(
    schema: Dict[str, Any], name: str, version: str, base_url: str
) -> str:
    """Generate YAML from JSON schema with examples and comments."""
    # Initialize ruamel.yaml
    yaml_obj = YAML()
    yaml_obj.preserve_quotes = True
    yaml_obj.width = 4096  # Prevent line wrapping
    # yaml_obj.indent(mapping=1, sequence=4, offset=1)
    # yaml_obj.map_indent = 1  # Ensure consistent indentation

    # Build the base structure with comments in a single pass
    template_data = CommentedMap(
        {
            "template_name": name,
            "template_version": version,
            "input": _generate_sample_from_schema(
                schema, with_comments=True, indent_level=0
            ),
        }
    )

    # Create output stream
    stream = io.StringIO()

    # Add header comments
    stream.write(f"# Application template configuration for: {name}\n")
    stream.write("# Fill in the values below to configure your application.\n")
    stream.write("# To use values from another app, use the following format:\n")
    stream.write("# my_param:\n")
    stream.write('#   type: "app-instance-ref"\n')
    stream.write('#   instance_id: "<app-instance-id>"\n')
    stream.write('#   path: "<path-from-get-values-response>"\n')

    schema_url = f"{base_url}/apis/apps/v2/templates/{name}/{version}/schema"
    stream.write(f"# yaml-language-server: $schema={schema_url}\n")

    stream.write("\n")

    # Dump the YAML
    yaml_obj.dump(template_data, stream)

    output = stream.getvalue()
    return output
