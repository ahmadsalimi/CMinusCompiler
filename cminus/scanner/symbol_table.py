from dataclasses import dataclass
from typing import List


KEYWORDS = [
    'if',
    'else',
    'endif',
    'void',
    'int',
    'repeat',
    'break',
    'until',
    'return'
]


@dataclass
class Id:
    lexeme: str
    address: int = None


class Scope:
    def __init__(self, parent: 'Scope' = None) -> None:
        self.parent = parent
        self._locals: List[Id] = []

    def append(self, lexeme: str, address: int = None, force: bool = False) -> Id:
        if force or (id_ := self.lookup(lexeme) is None):
            id_ = Id(lexeme, address)
            self._locals.append(id_)
        return id_

    def lookup(self, lexeme: str) -> Id:
        return next((id_ for id_ in self._locals
                     if id_.lexeme == lexeme),
                    self.parent.lookup(lexeme) if self.parent else None)


class SymbolTable:
    _instance: 'SymbolTable' = None

    @classmethod
    def instance(cls) -> 'SymbolTable':
        if cls._instance is None:
            cls._instance = SymbolTable()
        return cls._instance

    def __init__(self) -> None:
        self.declaring = False
        self._scopes = [Scope()]

    def create_scope(self) -> None:
        self._scopes.append(Scope(self._current_scope))

    def delete_scope(self) -> None:
        self._scopes.pop()

    @property
    def _current_scope(self) -> Scope:
        return self._scopes[-1]

    def add_symbol(self, lexeme: str, address: int = None) -> None:
        self._current_scope.append(lexeme, address, self.declaring)
        self.declaring = False

    def lookup(self, lexeme: str) -> Id:
        return self._current_scope.lookup(lexeme)
