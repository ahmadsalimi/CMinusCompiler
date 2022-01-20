
from dataclasses import dataclass
from typing import List, Union

from .pb import Operation, Value


@dataclass
class StackEntry:
    value: Union[Value, Operation]
    description: str = ''

    def __repr__(self) -> str:
        return f'{self.value} ({self.description})'

    def __str__(self) -> str:
        return self.__repr__()


class SemanticStack:

    def __init__(self) -> None:
        self._s: List[StackEntry] = []

    def push(self, item: Union[Value, Operation], description: str = '') -> None:
        self._s.append(StackEntry(item, description))

    def pop(self, return_description: bool = False) -> Union[Value, Operation]:
        entry = self._s.pop()
        if return_description:
            return entry.value, entry.description
        return entry.value

    def from_top(self, offset: int = 0, return_description: bool = False) -> Union[Value, Operation]:
        entry = self._s[-offset-1]
        if return_description:
            return entry.value, entry.description
        return entry.value

    @property
    def length(self) -> int:
        return len(self._s)
