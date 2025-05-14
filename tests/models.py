from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from src.ashredis.record_base import RecordBase, MISSING


@dataclass
class NestedLevel3(RecordBase):
    value: Optional[str] = MISSING
    number: Optional[int] = MISSING
    flag: Optional[bool] = MISSING


@dataclass
class NestedLevel2(RecordBase):
    name: Optional[str] = MISSING
    count: Optional[int] = MISSING
    nested3: Optional[NestedLevel3] = MISSING
    items: Optional[List[str]] = MISSING


@dataclass
class NestedLevel1(RecordBase):
    title: Optional[str] = MISSING
    nested2: Optional[NestedLevel2] = MISSING
    values: Optional[Dict[str, Any]] = MISSING
    created_at: Optional[int] = MISSING


@dataclass
class ComplexTestModel(RecordBase):
    string_field: Optional[str] = MISSING
    integer_field: Optional[int] = MISSING
    float_field: Optional[float] = MISSING
    boolean_field: Optional[bool] = MISSING
    list_field: Optional[List[str]] = MISSING
    dict_field: Optional[Dict[str, Any]] = MISSING
    nested_field: Optional[NestedLevel1] = MISSING
    timestamp: Optional[int] = MISSING
