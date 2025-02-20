from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    RAY_BOT = auto()
    POSITION_SIZING = auto()
    MARKET_CAP_UPDATE = auto()


@dataclass
class Event:
    event_type: EventType
    data: any
