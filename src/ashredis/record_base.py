import json
from dataclasses import asdict
from typing import Any


class MissingSentinel:
    def __eq__(self, other: Any) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return ""


MISSING: Any = MissingSentinel()


class RecordBase:
    def __post_init__(self):
        self.key = None
        self.loaded_hash = {}

    @property
    def is_load(self) -> bool:
        return True if self.loaded_hash else False

    @classmethod
    def category(cls) -> str:
        return cls.__name__

    def to_dict(self) -> dict:
        return self.__remove_none_values(asdict(self))

    def to_hash(self) -> dict:
        return self.__prepare_for_redis(asdict(self))

    def __prepare_for_redis(self, data: dict) -> dict:
        result = {}
        for k, v in data.items():
            if isinstance(v, dict):
                result[k] = json.dumps(self.__remove_none_values(v))
            elif isinstance(v, list):
                result[k] = json.dumps(v)
            elif isinstance(v, bool):
                result[k] = int(v)
            elif not isinstance(v, MissingSentinel):
                result[k] = v
        return result

    def __remove_none_values(self, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        return {
            k: self.__remove_none_values(v)
            for k, v in data.items()
            if not isinstance(v, MissingSentinel)
        }
