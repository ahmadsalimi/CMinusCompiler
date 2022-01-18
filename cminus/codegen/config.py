from dataclasses import dataclass

from .pb import Value


@dataclass
class CodeGenConfig:
    word_size: Value = Value.immediate(4)
    data_start: int = 0
    temp_start: int = 1000
    stack_start: int = 2000
