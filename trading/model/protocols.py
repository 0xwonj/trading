from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from trading.bot.core import Bot


class Action(Protocol):
    def execute(self, data: any, bot: "Bot") -> None:
        """
        Execute the action with the provided data and bot context.
        """


class Strategy(Protocol):
    def execute(self, data: any, bot: "Bot") -> None:
        """
        Execute the strategy logic with the given data and bot context.
        """
