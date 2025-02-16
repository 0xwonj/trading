from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from trading.bot.bot import Bot


class Action(Protocol):
    @abstractmethod
    async def execute(self, data: any, bot: "Bot") -> None:
        """Execute the action with the given data and bot instance."""
        pass


class Strategy(Protocol):
    @abstractmethod
    async def execute(self, data: any, bot: "Bot") -> None:
        """Execute the strategy with the given data and bot instance."""
        pass
