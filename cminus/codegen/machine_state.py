from typing import List

from ..scanner.symbol_table import IdType
from ..scanner.scanner import Token
from .pb import ProgramBlock
from .config import CodeGenConfig


class MachineState:

    def __init__(self, config: CodeGenConfig, pb: ProgramBlock) -> None:
        self._config = config
        self.data_address = config.data_start
        self.temp_address = config.temp_start
        self.stack_address = config.stack_start
        self.data_pointer = None
        self.temp_pointer = None
        self.arg_pointer: List[int] = []
        self.last_id: Token = None
        self.last_type: IdType = None
        self.last_function_name: str = None
        self.declaring_args: bool = False
        self.pb = pb
        self.set_exec = False

    def getvar(self, size: int = 1) -> int:
        address = self.data_address
        self.data_address += size * self._config.word_size.value
        return address

    def gettemp(self) -> int:
        address = self.temp_address
        self.temp_address += self._config.word_size.value
        return address
