r"""
Enhanced validation helpers for Pydantic models with strict configuration and comprehensive type checking.

This module provides base classes and utilities for creating Pydantic models
with custom validation logic, strict configuration, and comprehensive type checking.

Usage example:

    import re
    from validation_helpers import ValidatedValueModel

    class RelLinkToBillPage(ValidatedValueModel[str]):
        '''A relative link to a bill page'''

        @staticmethod
        def custom_validate(value: str) -> None:
            '''Check that the relative link to a bill page is valid'''
            if not re.match(r"^/bill/\d+/$", value):
                raise ValueError(f"Invalid bill rel link: {value}")

    # Usage
    try:
        link = RelLinkToBillPage(value="/bill/123/")
        print(link.value)  # Output: /bill/123/

        invalid_link = RelLinkToBillPage(value="/invalid/")  # This will raise a ValidationError
    except ValidationError as e:
        print(f"Validation error: {e}")

Note: This implementation ensures strict type checking and validation,
combining the benefits of Pydantic, typeguard, and custom validation logic.
"""

from abc import ABC, abstractmethod
from functools import total_ordering
from typing import Any, Dict, Protocol, Type, TypeVar

# from icecream import ic  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, model_serializer, model_validator
from typeguard import check_type, typechecked
from typing_extensions import ClassVar, Self

T = TypeVar("T")

STRICT_MODEL_CONFIG = ConfigDict(
    strict=True,
    extra="forbid",
    frozen=True,
    allow_inf_nan=False,
    arbitrary_types_allowed=True,
    populate_by_name=False,
    use_enum_values=False,
    str_strip_whitespace=True,
    str_max_length=10 * 1024 * 1024,  # 10 MB, for web page downloads
    str_min_length=1,  # No empty strings allowed
)


class StrictBaseModel(BaseModel):
    """A strict base model"""

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG


# Check if BaseModel has a custom_validate method
if hasattr(BaseModel, "custom_validate"):
    raise TypeError(
        "BaseModel already has a 'custom_validate' method. Please choose a different name for the custom validation method."
    )


from typing import Generic


@typechecked
@total_ordering
class ValidatedValueModel(StrictBaseModel, Generic[T], ABC):
    """Base class for single-value Pydantic models with custom validation and strict configuration."""

    value: T

    @staticmethod
    @abstractmethod
    def custom_validate(value: T) -> None:
        """
        Custom validation method to be implemented by subclasses.

        Args:
            value (T): The value to be validated.

        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclasses must implement custom_validate method")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        """
        Validates the model after initial creation.

        This method calls the custom_validate method to perform additional validation
        on the 'value' field and performs runtime type checking.

        Returns:
            Self: The validated model instance.

        Raises:
            ValueError: If the custom validation fails.
            TypeError: If the type of 'value' doesn't match the expected type.
        """
        value_type = self.get_value_type()
        check_type(self.value, value_type)

        # Check if the value is comparable
        if not hasattr(self.value, "__lt__"):
            raise TypeError(f"Value of type {type(self.value)} is not comparable")

        self.custom_validate(self.value)
        return self

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return bool(self.value < other.value)  # type: ignore[operator]

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    @abstractmethod
    def get_value_type(cls) -> Type[T]:
        """Return the type of the 'value' field."""
        raise NotImplementedError("Subclasses must implement get_value_type method")

    @model_validator(mode="before")
    @classmethod
    def deserialize_value(cls, data: Any) -> Any:
        expected_type = cls.get_value_type()
        if isinstance(data, expected_type):
            return {"value": data}
        return data

    @model_serializer
    def serialize(self) -> T:
        return self.value
