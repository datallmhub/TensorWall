"""Output Constraints Engine.

Validates LLM outputs against defined schemas and constraints.
Ensures responses conform to expected formats, especially in production.
"""

import json
import re
from typing import Optional, Any
from pydantic import BaseModel
from enum import Enum


class OutputFormat(str, Enum):
    """Expected output formats."""

    TEXT = "text"
    JSON = "json"
    JSON_SCHEMA = "json_schema"
    MARKDOWN = "markdown"


class OutputConstraint(BaseModel):
    """Output constraint configuration."""

    format: OutputFormat = OutputFormat.TEXT
    json_schema: Optional[dict] = None  # JSON Schema for validation
    max_length: Optional[int] = None  # Max character length
    min_length: Optional[int] = None  # Min character length
    must_contain: list[str] = []  # Required substrings
    must_not_contain: list[str] = []  # Forbidden substrings
    regex_pattern: Optional[str] = None  # Regex pattern to match
    strip_markdown: bool = False  # Strip markdown formatting


class OutputValidationResult(BaseModel):
    """Result of output validation."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    sanitized_output: Optional[str] = None  # Cleaned/transformed output
    extracted_json: Optional[dict] = None  # Extracted JSON if applicable


class OutputValidator:
    """
    Validates and transforms LLM outputs.

    Features:
    - JSON schema validation
    - Length constraints
    - Content filtering
    - Format enforcement
    - JSON extraction from text
    """

    def validate(
        self,
        output: str,
        constraint: OutputConstraint,
    ) -> OutputValidationResult:
        """
        Validate output against constraints.

        Args:
            output: The LLM output to validate
            constraint: Constraints to apply

        Returns:
            OutputValidationResult with validation status
        """
        errors = []
        warnings = []
        sanitized = output
        extracted_json = None

        # Length checks
        if constraint.max_length and len(output) > constraint.max_length:
            errors.append(
                f"Output exceeds max length: {len(output)} > {constraint.max_length}"
            )

        if constraint.min_length and len(output) < constraint.min_length:
            errors.append(
                f"Output below min length: {len(output)} < {constraint.min_length}"
            )

        # Content checks
        for required in constraint.must_contain:
            if required.lower() not in output.lower():
                errors.append(f"Output missing required content: '{required}'")

        for forbidden in constraint.must_not_contain:
            if forbidden.lower() in output.lower():
                errors.append(f"Output contains forbidden content: '{forbidden}'")

        # Regex pattern check
        if constraint.regex_pattern:
            if not re.search(constraint.regex_pattern, output):
                errors.append("Output does not match required pattern")

        # Format-specific validation
        if constraint.format == OutputFormat.JSON:
            json_result = self._validate_json(output)
            if not json_result["valid"]:
                errors.extend(json_result["errors"])
            else:
                extracted_json = json_result["json"]

        elif constraint.format == OutputFormat.JSON_SCHEMA:
            if not constraint.json_schema:
                warnings.append("JSON schema format specified but no schema provided")
            else:
                schema_result = self._validate_json_schema(
                    output, constraint.json_schema
                )
                if not schema_result["valid"]:
                    errors.extend(schema_result["errors"])
                else:
                    extracted_json = schema_result["json"]

        # Strip markdown if requested
        if constraint.strip_markdown:
            sanitized = self._strip_markdown(output)

        return OutputValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_output=sanitized,
            extracted_json=extracted_json,
        )

    def _validate_json(self, output: str) -> dict:
        """Validate that output is valid JSON."""
        # Try to extract JSON from the output
        json_str = self._extract_json(output)

        if not json_str:
            return {
                "valid": False,
                "errors": ["Output is not valid JSON"],
                "json": None,
            }

        try:
            parsed = json.loads(json_str)
            return {
                "valid": True,
                "errors": [],
                "json": parsed,
            }
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [f"Invalid JSON: {str(e)}"],
                "json": None,
            }

    def _validate_json_schema(self, output: str, schema: dict) -> dict:
        """Validate JSON output against a JSON schema."""
        # First validate it's JSON
        json_result = self._validate_json(output)
        if not json_result["valid"]:
            return json_result

        parsed = json_result["json"]

        # Validate against schema
        try:
            from jsonschema import validate, ValidationError as JsonSchemaError

            validate(instance=parsed, schema=schema)
            return {
                "valid": True,
                "errors": [],
                "json": parsed,
            }
        except ImportError:
            # jsonschema not installed, do basic validation
            return self._basic_schema_validation(parsed, schema)
        except JsonSchemaError as e:
            return {
                "valid": False,
                "errors": [f"Schema validation failed: {e.message}"],
                "json": parsed,
            }

    def _basic_schema_validation(self, data: Any, schema: dict) -> dict:
        """Basic JSON schema validation without jsonschema library."""
        errors = []

        # Check type
        expected_type = schema.get("type")
        if expected_type:
            type_map = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "null": type(None),
            }
            expected = type_map.get(expected_type)
            if expected and not isinstance(data, expected):
                errors.append(
                    f"Expected type '{expected_type}', got '{type(data).__name__}'"
                )

        # Check required properties for objects
        if isinstance(data, dict):
            required = schema.get("required", [])
            for prop in required:
                if prop not in data:
                    errors.append(f"Missing required property: '{prop}'")

            # Check properties exist
            properties = schema.get("properties", {})
            for prop, prop_schema in properties.items():
                if prop in data:
                    # Recursive validation for nested objects
                    if prop_schema.get("type") == "object":
                        nested_result = self._basic_schema_validation(
                            data[prop], prop_schema
                        )
                        errors.extend([f"{prop}.{e}" for e in nested_result["errors"]])

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "json": data,
        }

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text, handling code blocks and mixed content."""
        # Try direct parse first
        text = text.strip()
        if text.startswith(("{", "[")):
            return text

        # Try to find JSON in code blocks
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(code_block_pattern, text)
        for match in matches:
            match = match.strip()
            if match.startswith(("{", "[")):
                return match

        # Try to find JSON objects/arrays in text
        json_patterns = [
            r"(\{[\s\S]*\})",  # Object
            r"(\[[\s\S]*\])",  # Array
        ]
        for pattern in json_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue

        return None

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown formatting from text."""
        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)

        # Remove headers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove bold/italic
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Remove links
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)

        # Remove horizontal rules
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # Remove blockquotes
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

        # Clean up extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        return text

    def enforce_json_output(
        self,
        output: str,
        schema: Optional[dict] = None,
    ) -> OutputValidationResult:
        """
        Convenience method to enforce JSON output.

        Args:
            output: LLM output
            schema: Optional JSON schema

        Returns:
            Validation result with extracted JSON
        """
        constraint = OutputConstraint(
            format=OutputFormat.JSON_SCHEMA if schema else OutputFormat.JSON,
            json_schema=schema,
        )
        return self.validate(output, constraint)


# Singleton instance
output_validator = OutputValidator()


# Pre-defined schemas for common use cases
COMMON_SCHEMAS = {
    "classification": {
        "type": "object",
        "required": ["label", "confidence"],
        "properties": {
            "label": {"type": "string"},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
        },
    },
    "extraction": {
        "type": "object",
        "required": ["entities"],
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "value"],
                    "properties": {
                        "type": {"type": "string"},
                        "value": {"type": "string"},
                        "context": {"type": "string"},
                    },
                },
            },
        },
    },
    "sentiment": {
        "type": "object",
        "required": ["sentiment", "score"],
        "properties": {
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral"],
            },
            "score": {"type": "number"},
        },
    },
    "summary": {
        "type": "object",
        "required": ["summary"],
        "properties": {
            "summary": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
        },
    },
    "qa": {
        "type": "object",
        "required": ["answer"],
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number"},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
    },
}
