from enum import Enum


class StreamEvent(Enum):
    SAVE = "save"
    UPDATE = "update"


class DefaultKeys(Enum):
    STREAM_KEY = "stream"
