from dataclasses import is_dataclass
from typing import TypeVar, Type, get_type_hints, get_origin, get_args, Union

from src.ashredis import RecordBase

T = TypeVar("T", bound=RecordBase)


def dict_to_dataclass(cls: Type[T], data: dict) -> T:
    """Converts a dictionary to a dataclass, including nested dataclasses."""
    hints = get_type_hints(cls)
    kwargs = {}

    for field, field_type in hints.items():
        if field not in data:
            continue

        value = data[field]

        if get_origin(field_type) is Union:
            field_type = get_args(field_type)[0]

        if is_dataclass(field_type) and isinstance(value, dict):
            kwargs[field] = dict_to_dataclass(field_type, value)
        else:
            kwargs[field] = value

    return cls(**kwargs)
