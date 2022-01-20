from dataclasses import dataclass, field
from enum import Enum
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


class IdType(Enum):
    Int = 'int'
    Void = 'void'
    Array = 'array'
    Function = 'function'
    NotSpecified = 'not_specified'


@dataclass
class Id:
    lexeme: str
    address: int = None
    type: IdType = IdType.NotSpecified
    args_type: List[IdType] = field(default_factory=list)
    return_type: IdType = IdType.NotSpecified


class Scope:
    def __init__(self, parent: 'Scope' = None) -> None:
        self.parent = parent
        self._locals: List[Id] = []

    def append(self, lexeme: str, address: int = None) -> Id:
        id_ = Id(lexeme, address)
        self._locals.append(id_)
        return id_

    def lookup(self, lexeme: str) -> Id:
        return next((id_ for id_ in self._locals
                     if id_.lexeme == lexeme),
                    self.parent.lookup(lexeme) if self.parent else None)

    def lookup_by_instno(self, instno: int) -> Id:
        return next((id_ for id_ in self._locals
                     if id_.address == instno
                     and id_.type == IdType.Function),
                    self.parent.lookup_by_instno(instno) if self.parent else None)

    def lookup_by_address(self, address: int) -> Id:
        return next((id_ for id_ in self._locals
                     if id_.address == address
                     and id_.type != IdType.Function),
                    self.parent.lookup_by_address(address) if self.parent else None)


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

    def add_symbol(self, lexeme: str, address: int = None, force: bool = False) -> Id:
        if self.declaring or force:
            self.declaring = False
            return self._current_scope.append(lexeme, address)

    def lookup(self, lexeme: str) -> Id:
        return self._current_scope.lookup(lexeme)

    def lookup_by_instno(self, instno: int) -> Id:
        return self._current_scope.lookup_by_instno(instno)

    def lookup_by_address(self, address: int) -> Id:
        return self._current_scope.lookup_by_address(address)
