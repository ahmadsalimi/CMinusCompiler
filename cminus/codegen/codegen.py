from enum import Enum
from typing import Callable, Dict, Protocol

from ..scanner.symbol_table import SymbolTable
from .scope import ScopeManager, ScopeType
from .ar import ActivationsStack, RegisterFile
from .machine_state import MachineState
from ..scanner.scanner import Token
from .config import Config
from .semantic_stack import SemanticStack
from .pb import Instruction, ProgramBlock, Value, Operation


class Routine(Protocol):
    def __call__(self, codegen: 'CodeGenerator', token: Token = None) -> None: ...


class Symbols:
    symbols: Dict['ActionSymbol', Routine] = {}

    @classmethod
    def symbol(cls, symbol: 'ActionSymbol') -> Callable[[Routine], Routine]:
        def _symbol(routine: Routine):
            def wrapper(codegen: 'CodeGenerator', token: Token) -> None:
                if routine.__code__.co_argcount == 2:
                    return routine(codegen, token)
                return routine(codegen)
            cls.symbols[symbol] = wrapper
            return wrapper
        return _symbol


class ActionSymbol(Enum):
    Pid = 'pid'
    Pnum = 'pnum'
    Pzero = 'pzero'
    Prv = 'prv'
    Parray = 'parray'
    Pop = 'pop'
    DeclareArray = 'declare_array'
    DeclareFunction = 'declare_function'
    DeclareId = 'declare_id'
    Assign = 'assign'
    OpExec = 'op_exec'
    OpPush = 'op_push'
    Hold = 'hold'
    Label = 'label'
    Decide = 'decide'
    Case = 'case'
    JumpWhile = 'jump_while'
    Output = 'output'
    FunctionCall = 'function_call'
    FunctionReturn = 'function_return'
    ArgInit = 'arg_init'
    ArgFinish = 'arg_finish'
    ArgPass = 'arg_pass'
    FunctionScope = 'function_scope'
    ContainerScope = 'container_scope'
    TemporaryScope = 'temporary_scope'
    SimpleScope = 'simple_scope'
    ScopeStart = 'scope_start'
    ScopeEnd = 'scope_end'
    Prison = 'prison'
    PrisonBreak = 'prison_break'
    SetExec = 'set_exec'

    def call(self, codegen: 'CodeGenerator', token: Token = None) -> None:
        self.value(codegen, token)


class CodeGenerator:

    def __init__(self, config: Config) -> None:
        self._config = config
        self._pb = ProgramBlock()
        self._state = MachineState(config, self._pb)
        self._rf = RegisterFile(self._state.getvar(),
                                self._state.getvar(),
                                self._state.getvar(),
                                self._state.getvar())
        self._as = ActivationsStack(config, self._pb, self._rf)
        self._scope = ScopeManager(self._state, self._pb)
        self._ss = SemanticStack()
        self.template()

    def template(self) -> None:
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(self._config.stack_start),
                        Value.direct(self._rf.sp)))
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(self._config.stack_start),
                        Value.direct(self._rf.fp)))
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(9999),
                        Value.direct(self._rf.ra)))
        self._pb.append(Instruction(Operation.Assign,   # is it necessary?
                        Value.immediate(9999),
                        Value.direct(self._rf.rv)))

        self._pb.append(Instruction(Operation.Jp, Value.direct(9))) # jp to main address
        self._as.pop(Value.direct(self._rf.rv))
        self._pb.append(Instruction(Operation.Print, Value.direct(self._rf.rv)))
        self._pb.append(Instruction(Operation.Jp, Value.indirect(self._rf.ra)))
        self._state.getvar()

    def execute_from(self, function_name: str) -> None:
        id_ = SymbolTable.instance().lookup(function_name)
        self._pb[self._ss.pop()] = Instruction(Operation.Jp, Value.direct(id_.address))

    def action(self, symbol: 'ActionSymbol', token: Token):
        symbol.call(self, token)

    @Symbols.symbol(ActionSymbol.Pid)
    def pid(self, token: Token) -> None:
        id_ = SymbolTable.instance().lookup(token)
        self._ss.push(Value.direct(id_.address))

    @Symbols.symbol(ActionSymbol.Pnum)
    def pnum(self, token: Token) -> None:
        self._ss.push(Value.immediate(int(token.lexeme)))

    @Symbols.symbol(ActionSymbol.Pzero)
    def pzero(self) -> None:
        self._ss.push(Value.immediate(0))

    @Symbols.symbol(ActionSymbol.Prv)
    def prv(self) -> None:
        self._ss.push(Value.direct(self._rf.rv))

    @Symbols.symbol(ActionSymbol.Parray)
    def parray(self) -> None:
        offset = self._ss.pop()
        base = self._ss.pop()
        t = self._state.gettemp()
        self._pb.append(Instruction(Operation.Mult, self._config.word_size, offset, Value.direct(t)))
        self._pb.append(Instruction(Operation.Add, base, Value.direct(t), Value.direct(t)))
        self._ss.push(Value.indirect(t))

    @Symbols.symbol(ActionSymbol.Pop)
    def pop(self) -> None:
        self._as.pop(self._ss.pop())

    @Symbols.symbol(ActionSymbol.DeclareArray)
    def declare_array(self) -> None:
        size = self._ss.pop().pure
        base = self._ss.from_top()
        self._pb.append(Instruction(Operation.Assign,
                        Value.direct(self._rf.sp), base))                        
        self._as.reserve(size)

    @Symbols.symbol(ActionSymbol.DeclareFunction)
    def declare_function(self) -> None:
        self._state.data_pointer = self._state.data_address
        self._state.temp_pointer = self._state.temp_address
        self._pb[self._pb.i] = Instruction.empty()  # TODO: why?
        id_ = SymbolTable.instance().lookup(self._state.last_token)
        id_.address = self._pb.i + 1

    @Symbols.symbol(ActionSymbol.DeclareId)
    def declare_id(self, token: Token) -> None:
        id_ = SymbolTable.instance().lookup(token)
        id_.address = self._state.getvar()
        self._state.last_token = token

        if self._state.declaring_args:
            self._as.pop(Value.direct(id_.address))
        else:
            self._pb.append(Instruction(Operation.Assign,
                            Value.immediate(0),
                            Value.direct(id_.address)))

    @Symbols.symbol(ActionSymbol.Assign)
    def assign(self) -> None:
        self._pb.append(Instruction(Operation.Assign,
                        self._ss.pop(),
                        self._ss.from_top()))

    @Symbols.symbol(ActionSymbol.OpExec)
    def op_exec(self) -> None:
        arg2 = self._ss.pop()
        op: Operation = self._ss.pop()
        arg1 = self._ss.pop()
        t = Value.direct(self._state.gettemp())
        self._pb.append(Instruction(op, arg1, arg2, t))

    @Symbols.symbol(ActionSymbol.OpPush)
    def op_push(self, token: Token) -> None:
        self._ss.push(Operation.from_symbol(token.lexeme))

    @Symbols.symbol(ActionSymbol.Hold)
    def hold(self) -> None:
        self.label()
        self._pb.append(Instruction.empty())

    @Symbols.symbol(ActionSymbol.Label)
    def label(self) -> None:
        self._ss.push(Value.direct(self._pb.i))

    @Symbols.symbol(ActionSymbol.Decide)
    def decide(self) -> None:
        address = self._ss.pop()
        condition = self._ss.pop()
        self._pb.append(Instruction(Operation.Jpf, condition, address))

    @Symbols.symbol(ActionSymbol.Case)
    def case(self) -> None:
        t = Value.direct(self._state.gettemp())
        arg1 = self._ss.pop()
        arg2 = self._ss.from_top()
        self._pb.append(Instruction(Operation.Eq, arg1, arg2, t))
        self._ss.push(t)

    @Symbols.symbol(ActionSymbol.JumpWhile)
    def jump_while(self) -> None:
        top1 = self._ss.pop()
        top2 = self._ss.pop()
        label = self._ss.pop()
        self._pb.append(Instruction(Operation.Jp, label))
        self._ss.push(top2)
        self._ss.push(top1)

    @Symbols.symbol(ActionSymbol.Output)
    def output(self) -> None:
        self._pb.append(Instruction(Operation.Print, self._ss.pop()))

    @Symbols.symbol(ActionSymbol.FunctionCall)
    def function_call(self) -> None:
        self.store()
        self.push_args()
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(self._pb.i + 3),
                        Value.direct(self._rf.ra)))
        self._pb.append(Instruction(Operation.Jp, Value.direct(self._ss.pop())))
        self.restore()
        self.collect()

    def store(self) -> None:
        for address in range(self._state.data_pointer, self._state.data_address, self._config.word_size.pure):
            self._as.push(Value.direct(address))
        for address in range(self._state.temp_pointer, self._state.temp_address, self._config.word_size.pure):
            self._as.push(Value.direct(address))
        self._as.push_rf()

    def push_args(self) -> None:
        for _ in range(self._state.arg_pointer.pop(), self._ss.length()):
            self._as.push(self._ss.pop())

    def restore(self) -> None:
        self._as.pop_rf()
        for address in range(self._state.temp_address, self._state.temp_pointer, -self._config.word_size.pure):
            self._as.pop(Value.direct(address - self._config.word_size.pure))
        for address in range(self._state.data_address, self._state.data_pointer, -self._config.word_size.pure):
            self._as.pop(Value.direct(address - self._config.word_size.pure))

    def collect(self) -> None:
        t = Value.direct(self._state.gettemp())
        self._pb.append(Instruction(Operation.Assign,
                        Value.direct(self._rf.rv), t))
        self._ss.push(t)

    @Symbols.symbol(ActionSymbol.FunctionReturn)
    def function_return(self) -> None:
        self._pb.append(Instruction(Operation.Jp, Value.indirect(self._rf.ra)))

    @Symbols.symbol(ActionSymbol.ArgInit)
    def arg_init(self) -> None:
        self._state.declaring_args = True

    @Symbols.symbol(ActionSymbol.ArgFinish)
    def arg_finish(self) -> None:
        self._state.declaring_args = False

    @Symbols.symbol(ActionSymbol.ArgPass)
    def arg_pass(self) -> None:
        self._state.arg_pointer.append(self._ss.length)

    @Symbols.symbol(ActionSymbol.FunctionScope)
    def function_scope(self) -> None:
        self._scope.push_type(ScopeType.Function)

    @Symbols.symbol(ActionSymbol.ContainerScope)
    def container_scope(self) -> None:
        self._scope.push_type(ScopeType.Container)

    @Symbols.symbol(ActionSymbol.TemporaryScope)
    def temporary_scope(self) -> None:
        self._scope.push_type(ScopeType.Temporary)

    @Symbols.symbol(ActionSymbol.SimpleScope)
    def simple_scope(self) -> None:
        self._scope.push_type(ScopeType.Simple)

    @Symbols.symbol(ActionSymbol.ScopeStart)
    def scope_start(self) -> None:
        SymbolTable.instance().create_scope()
        self._scope.create_scope()

    @Symbols.symbol(ActionSymbol.ScopeEnd)
    def scope_end(self) -> None:
        SymbolTable.instance().delete_scope()
        self._scope.delete_scope()

    @Symbols.symbol(ActionSymbol.Prison)
    def prison(self) -> None:
        self._scope.prison()

    @Symbols.symbol(ActionSymbol.PrisonBreak)
    def prison_break(self) -> None:
        self._scope.prison_break()

    @Symbols.symbol(ActionSymbol.SetExec)
    def set_exec(self) -> None:
        if self._state.set_exec:
            return
        self._state.set_exec = True
        function = self._ss.pop()
        self._pb.i -= 1
        self.hold()
        self._ss.push(function)
