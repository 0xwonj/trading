from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    PRICE_UPDATE = "PRICE_UPDATE"
    ORDER_FILLED = "ORDER_FILLED"
    RAY_BOT = "RAY_BOT"


@dataclass
class Event:
    event_type: EventType
    data: any
