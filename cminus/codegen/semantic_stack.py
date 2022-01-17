
from typing import List, Union
from .pb import Operation, Value


class SemanticStack:

    def __init__(self) -> None:
        self._s: List[Union[Value, Operation]] = []

    def push(self, item: Union[Value, Operation]) -> None:
        self._s.append(item)

    def pop(self) -> Union[Value, Operation]:
        return self._s.pop()

    def from_top(self, offset: int = 0) -> Union[Value, Operation]:
        return self._s[-offset-1]

    @property
    def length(self) -> int:
        return len(self._s)
