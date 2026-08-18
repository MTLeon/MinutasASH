from __future__ import annotations

import unittest

from pydantic import BaseModel, ConfigDict, ValidationError

from src.providers.structured_validation import validate_model_json


class StrictItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str


class StrictResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[StrictItem]


class StructuredValidationTests(unittest.TestCase):
    def test_unknown_nested_model_metadata_is_removed(self) -> None:
        result = validate_model_json(
            '{"items":[{"description":"Acuerdo","modelo":"claude"}],"debug":true}',
            StrictResult,
        )

        self.assertEqual(result.items[0].description, "Acuerdo")
        self.assertEqual(result.model_dump(), {"items": [{"description": "Acuerdo"}]})

    def test_required_fields_remain_strict(self) -> None:
        with self.assertRaises(ValidationError):
            validate_model_json('{"items":[{"modelo":"claude"}]}', StrictResult)

    def test_field_types_remain_strict(self) -> None:
        with self.assertRaises(ValidationError):
            validate_model_json('{"items":[{"description":42,"modelo":"claude"}]}', StrictResult)


if __name__ == "__main__":
    unittest.main()
