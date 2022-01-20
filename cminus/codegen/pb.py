from ctypes import Union
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from ..scanner.symbol_table import IdType


class Operation(Enum):
    Add = 'ADD'
    Mult = 'MULT'
    Sub = 'SUB'
    Eq = 'EQ'
    Lt = 'LT'
    Assign = 'ASSIGN'
    Jpf = 'JPF'
    Jp = 'JP'
    Print = 'PRINT'
    Empty = ''

    @staticmethod
    def from_symbol(symbol: str) -> 'Operation':
        return OPERATIONS[symbol]


OPERATIONS: Dict[str, Operation] = {
    '+': Operation.Add,
    '-': Operation.Sub,
    '*': Operation.Mult,
    '<': Operation.Lt,
    '==': Operation.Eq,
}


@dataclass
class Value:
    prefix: str = ''
    value: int = None
    type: IdType = IdType.NotSpecified

    @staticmethod
    def immediate(value: int, type: IdType = IdType.NotSpecified) -> 'Value':
        return Value('#', value, type=type)

    @staticmethod
    def indirect(value: int, type: IdType = IdType.NotSpecified) -> 'Value':
        return Value('@', value, type=type)

    @staticmethod
    def direct(value: int, type: IdType = IdType.NotSpecified) -> 'Value':
        return Value(value=value, type=type)

    @staticmethod
    def empty() -> 'Value':
        return Value()

    def __repr__(self) -> str:
        return f'{self.prefix}{self.value if self.value is not None else ""}'

    def __str__(self) -> str:
        return self.__repr__()


@dataclass
class Instruction:
    op: Operation
    arg1: Value
    arg2: Value = Value.empty()
    arg3: Value = Value.empty()

    @staticmethod
    def empty() -> 'Instruction':
        return Instruction(Operation.Empty, Value.empty())

    def __repr__(self) -> str:
        return f'({self.op.value}, {self.arg1}, {self.arg2}, {self.arg3})' if self.op != Operation.Empty else ''


class ProgramBlock:

    def __init__(self) -> None:
        self._instructions: List[Union[Instruction]] = []

    @property
    def i(self) -> int:
        return len(self._instructions)

    @i.setter
    def i(self, value: int) -> None:
        if value < self.i:
            self._instructions = self._instructions[:value]
        else:
            self._instructions.extend([Instruction.empty() for _ in range(value - self.i)])

    def append(self, value: Instruction) -> None:
        self._instructions.append(value)

    def __setitem__(self, index: int, value: Instruction) -> None:
        self._instructions[index] = value

    def __str__(self) -> str:
        return '\n'.join([f'{i}\t{inst}' for i, inst in enumerate(self._instructions)])
