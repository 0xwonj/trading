from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    RAY_BOT = auto()
    PRICE_UPDATE = auto()
    POSITION_SIZING = auto()


@dataclass
class Event:
    event_type: EventType
    data: any
