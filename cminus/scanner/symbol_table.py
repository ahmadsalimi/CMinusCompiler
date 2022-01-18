from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .scanner import Token


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
    token: 'Token'
    scope: 'Scope'
    address: int = None


class Scope:
    def __init__(self, parent: 'Scope' = None) -> None:
        self.parent = parent
        self._locals: List[Id] = []

    def append(self, token: 'Token', force: bool = False) -> Id:
        if force or (id_ := self.lookup(token) is None):
            id_ = Id(token, self)
            self._locals.append(id_)
        return id_

    def lookup(self, token: 'Token') -> Id:
        return next((id_ for id_ in self._locals
                     if id_.token == token),
                    self.parent.lookup(token) if self.parent else None)


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

    def add_symbol(self, token: 'Token') -> None:
        self._current_scope.append(token, self.declaring)
        self.declaring = False

    def lookup(self, token: 'Token') -> Id:
        return self._current_scope.lookup(token)

    def clear(self) -> None:
        self._scopes = [Scope()]


