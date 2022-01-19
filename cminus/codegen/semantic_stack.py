
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

    def pop(self) -> Union[Value, Operation]:
        return self._s.pop().value

    def from_top(self, offset: int = 0) -> Union[Value, Operation]:
        return self._s[-offset-1].value

    @property
    def length(self) -> int:
        return len(self._s)
