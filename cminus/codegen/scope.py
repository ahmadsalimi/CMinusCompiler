from enum import Enum
from typing import List

from .pb import Instruction, Operation, Value
from .machine_state import MachineState
from .ar import ActivationsStack


class Layer:
    def __init__(self, state: MachineState) -> None:
        self._state = state
        self._data_stack: List[int] = []
        self._temp_stack: List[int] = []
        self._jail: List[int] = []

    def create_scope(self) -> None:
        self._temp_stack.append(self._state.temp_address)
        self._data_stack.append(self._state.data_address)
        self._jail.append('|')

    def delete_scope(self) -> None:
        self._state.data_address = self._data_stack.pop()
        self._state.temp_address = self._temp_stack.pop()

        while self._jail[-1] != '|':
            self.prison_break()
        self._jail.pop()

    def are_we_inside(self) -> bool:
        return len(self._data_stack) > 0

    def prison(self) -> None:
        self._jail.append(self._state.pb.i)
        self._state.pb.i += 1

    def prison_break(self) -> None:
        break_address = Value.direct(self._state.pb.i)
        prisoner = self._jail.pop()
        self._state.pb[prisoner] = Instruction(Operation.Jp, break_address)


class ScopeType(Enum):
    Function = 'function'
    Temporary = 'temporary'
    Simple = 'simple'
    Container = 'container'


class ScopeManager:

    def __init__(self, state: MachineState, as_: ActivationsStack) -> None:
        self._state = state
        self._as = as_
        self._delete = False
        self._layers = {
            ScopeType.Function: Layer(state),
            ScopeType.Temporary: Layer(state),
            ScopeType.Simple: Layer(state),
            ScopeType.Container: Layer(state)
        }
        self._types: List[ScopeType] = []

    def push_type(self, type_: ScopeType) -> None:
        if self._delete:
            self._delete = False
            self._layers[type_].delete_scope()
            if type_ == ScopeType.Function:
                self._as.delete_scope()
        else:
            self._types.append(type_)

    def prison(self) -> None:
        self._layers[self._types.pop()].prison()

    def prison_break(self) -> None:
        self._layers[self._types.pop()].prison_break()

    def are_we_inside(self, type: ScopeType) -> bool:
        return self._layers[type].are_we_inside()

    def create_scope(self) -> None:
        type_ = self._types.pop()
        self._layers[type_].create_scope()
        if type_ == ScopeType.Function:
            self._as.create_scope()

    def delete_scope(self) -> None:
        self._delete = True
