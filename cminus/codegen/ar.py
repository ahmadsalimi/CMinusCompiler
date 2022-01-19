from dataclasses import dataclass

from .config import CodeGenConfig
from .pb import Instruction, Operation, ProgramBlock, Value


@dataclass
class RegisterFile:
    sp: int
    fp: int
    ra: int
    rv: int


class ActivationsStack:

    def __init__(self, config: CodeGenConfig, pb: ProgramBlock, rf: RegisterFile) -> None:
        self._config = config
        self._pb = pb
        self._rf = rf

    def push(self, value: Value) -> None:
        self._pb.append(Instruction(Operation.Assign,
                        value, Value.indirect(self._rf.sp)))
        self._pb.append(Instruction(Operation.Add,
                        Value.direct(self._rf.sp),
                        self._config.word_size,
                        Value.direct(self._rf.sp)))

    def pop(self, address: Value) -> None:
        self._pb.append(Instruction(Operation.Sub,
                        Value.direct(self._rf.sp),
                        self._config.word_size,
                        Value.direct(self._rf.sp)))
        self._pb.append(Instruction(Operation.Assign,
                        Value.indirect(self._rf.sp), address))

    def create_scope(self) -> None:
        self.push(self._rf.fp)
        self._pb.append(Instruction(Operation.Assign,
                        Value.direct(self._rf.sp),
                        Value.direct(self._rf.fp)))

    def delete_scope(self) -> None:
        self._pb.append(Instruction(Operation.Assign,
                        Value.direct(self._rf.fp),
                        Value.direct(self._rf.sp)))
        self.pop(self._rf.fp)

    def reserve(self, size: int) -> None:
       for _ in range(size):
            self.push(Value.immediate(0))

    def push_rf(self) -> None:
        self.push(Value.direct(self._rf.sp))
        self.push(Value.direct(self._rf.fp))
        self.push(Value.direct(self._rf.ra))

    def pop_rf(self) -> None:
        self.pop(Value.direct(self._rf.ra))
        self.pop(Value.direct(self._rf.fp))
        self.pop(Value.direct(self._rf.sp))
