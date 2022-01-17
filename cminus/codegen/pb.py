from ctypes import Union
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class Operation(Enum):
    Add = 'ADD'
    Mult = 'MULT',
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
        return Operation(OPERATIONS[symbol])


OPERATIONS: Dict[str, Operation] = {
    '+': Operation.Add,
    '-': Operation.Sub,
    '*': Operation.Mul,
    '<': Operation.Lt,
    '==': Operation.Eq,
}


class Value:
    def __init__(self, value: str):
        self.value = value

    @staticmethod
    def immediate(value: int) -> 'Value':
        return Value(f'#{value}')

    @staticmethod
    def indirect(value: int) -> 'Value':
        return Value(f'@{value}')

    @staticmethod
    def direct(value: int) -> 'Value':
        return Value(f'{value}')

    @staticmethod
    def empty() -> 'Value':
        return Value('')

    @property
    def pure(self) -> int:
        return int(self.value[1:] if self.value[0] in '#@' else self.value)


@dataclass
class Instruction:
    op: Operation
    arg1: Value
    arg2: Value = Value.empty()
    arg3: Value = Value.empty()

    @staticmethod
    def empty() -> 'Instruction':
        return Instruction(Operation.Empty, Value.empty())


class ProgramBlock:

    def __init__(self) -> None:
        self._instructions: List[Union[Instruction]] = []

    @property
    def i(self) -> int:
        return len(self._instructions) - 1

    @i.setter
    def i(self, value: int) -> None:
        if value == self.i:
            return
        if value < self.i:
            self._instructions = self._instructions[:value]
        else:
            self._instructions.extend([Instruction.empty() for _ in range(value - self.i)])
            self._instructions[value] = value

    def append(self, value: Instruction) -> None:
        self._instructions.append(value)

    def __setitem__(self, index: int, value: Instruction) -> None:
        self._instructions[index] = value
