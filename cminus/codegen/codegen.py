from enum import Enum
from typing import Callable, Dict, List, Protocol

from .error_logger import CodeGenErrorLogger
from ..scanner.symbol_table import IdType, SymbolTable
from .scope import ScopeManager, ScopeType
from .ar import ActivationsStack, RegisterFile
from .machine_state import MachineState
from ..scanner.scanner import Token
from .config import CodeGenConfig
from .semantic_stack import SemanticStack
from .pb import Instruction, ProgramBlock, Value, Operation


class Routine(Protocol):
    def __call__(self, codegen: 'CodeGenerator', token: Token = None) -> None: ...


class Symbols:
    symbols: Dict['ActionSymbol', Routine] = {}

    @classmethod
    def symbol(cls, symbol: 'ActionSymbol') -> Callable[[Routine], Routine]:
        def _symbol(routine: Routine):
            def wrapper(codegen: 'CodeGenerator', token: Token = None) -> None:
                if routine.__code__.co_argcount == 2:
                    return routine(codegen, token)
                return routine(codegen)
            cls.symbols[symbol] = wrapper
            return wrapper
        return _symbol


class ActionSymbol(Enum):
    Output = 'output'
    JpFrom = 'jp_from'
    InitRf = 'init_rf'
    Pid = 'pid'
    Pnum = 'pnum'
    Prv = 'prv'
    Parray = 'parray'
    Ptype = 'ptype'
    Pop = 'pop'
    DeclareArray = 'declare_array'
    ArrayType = 'array_type'
    DeclareFunction = 'declare_function'
    CaptureParamType = 'capture_param_type'
    DeclareId = 'declare_id'
    Declare = 'declare'
    Assign = 'assign'
    OpExec = 'op_exec'
    OpPush = 'op_push'
    Hold = 'hold'
    Label = 'label'
    Decide = 'decide'
    JpfRepeat = 'jpf_repeat'
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
    ExecMain = 'exec_main'
    SetMainRa = 'set_main_ra'
    CheckDeclarationType = 'check_declaration_type'
    CheckInContainer = 'check_in_container'

    def __str__(self) -> str:
        return f'#{self.value}'


class CodeGenerator:
    instance: 'CodeGenerator' = None

    def __init__(self, config: CodeGenConfig) -> None:
        CodeGenerator.instance = self
        self._config = config
        self._pb = ProgramBlock()
        self._state = MachineState(config, self._pb)
        self._rf = RegisterFile(self._state.getvar(),
                                self._state.getvar(),
                                self._state.getvar(),
                                self._state.getvar())
        self._as = ActivationsStack(config, self._pb, self._rf)
        self._scope = ScopeManager(self._state, self._as)
        self._ss = SemanticStack()

    def export(self) -> str:
        """ Exports the program block to a string. """
        return str(self._pb)

    @Symbols.symbol(ActionSymbol.Output)
    def output(self) -> None:
        """ Implicit implementation of built-in output function. """
        id_ = SymbolTable.instance().add_symbol('output', self._pb.i, force=True)
        id_.type = IdType.Function
        id_.args_type.append(IdType.Int)
        self._as.pop(Value.direct(self._rf.rv))
        self._pb.append(Instruction(Operation.Print, Value.direct(self._rf.rv)))
        self._pb.append(Instruction(Operation.Jp, Value.indirect(self._rf.ra)))

    @Symbols.symbol(ActionSymbol.JpFrom)
    def jp_from(self) -> None:
        """ Jumps from the line in the semantic stack to current line. """
        line = self._ss.pop().value
        self._pb[line] = Instruction(Operation.Jp, Value.direct(self._pb.i))

    @Symbols.symbol(ActionSymbol.InitRf)
    def init_rf(self) -> None:
        """ Initializes register file. """
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(self._config.stack_start),
                        Value.direct(self._rf.sp)))
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(self._config.stack_start),
                        Value.direct(self._rf.fp)))
        self.hold() # for assigning the return address at #set_main_ra
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(0),
                        Value.direct(self._rf.rv)))

    @Symbols.symbol(ActionSymbol.Pid)
    def pid(self, token: Token) -> None:
        """ Pushes the id to the semantic stack.

        Args:
            token (Token): Id token.
        """
        id_ = SymbolTable.instance().lookup(token.lexeme)
        if id_ == None:
            CodeGenErrorLogger.instance.log(token.lineno, f"'{token.lexeme}' is not defined.")
            self._ss.push(Value.immediate(-1, IdType.NotSpecified), f'pid {token.lexeme} (undefined)')
        else:
            self._ss.push(Value.direct(id_.address, id_.type), f'pid {token.lexeme}')

    @Symbols.symbol(ActionSymbol.Pnum)
    def pnum(self, token: Token) -> None:
        """ Pushes the number to the semantic stack.

        Args:
            token (Token): Number token.
        """
        self._ss.push(Value.immediate(int(token.lexeme), IdType.Int), 'pnum')

    @Symbols.symbol(ActionSymbol.Prv)
    def prv(self) -> None:
        """ Pushes the return value to the semantic stack. """
        self._ss.push(Value.direct(self._rf.rv), 'prv')

    @Symbols.symbol(ActionSymbol.Parray)
    def parray(self) -> None:
        """ Calculates the array offset and pushes the address
        to the semantic stack. """
        offset = self._ss.pop()
        base = self._ss.pop()
        t = self._state.gettemp()
        self._pb.append(Instruction(Operation.Mult, self._config.word_size, offset, Value.direct(t)))
        self._pb.append(Instruction(Operation.Add, base, Value.direct(t), Value.direct(t)))
        self._ss.push(Value.indirect(t, IdType.Int), 'parray')

    @Symbols.symbol(ActionSymbol.Ptype)
    def ptype(self, token: Token) -> None:
        """ Pushes the type to the semantic stack.

        Args:
            token (Token): Type token.
        """
        self._state.last_type = IdType(token.lexeme)

    @Symbols.symbol(ActionSymbol.CheckDeclarationType)
    def check_declaration_type(self) -> None:
        """ Checks the type of the variable in the semantic stack to be int. """
        type_ = self._state.last_type
        token = self._state.last_id
        if type_ != IdType.Int:
            CodeGenErrorLogger.instance.log(token.lineno, f"Illegal type of {type_.value} for '{token.lexeme}'.")

    @Symbols.symbol(ActionSymbol.Pop)
    def pop(self) -> None:
        """ Pops from the semantic stack. """
        self._ss.pop()

    @Symbols.symbol(ActionSymbol.DeclareArray)
    def declare_array(self) -> None:
        """ Declares an array and reserves memory for it. """
        size = self._ss.pop().value
        base = self._ss.from_top()
        self._pb.append(Instruction(Operation.Assign,
                        Value.direct(self._rf.sp), base))                        
        self._as.reserve(size)
        SymbolTable.instance().lookup_by_address(base.value).type = IdType.Array

    @Symbols.symbol(ActionSymbol.ArrayType)
    def array_type(self) -> None:
        """ Sets the argument type to array """
        SymbolTable.instance().lookup(self._state.last_id.lexeme).type = IdType.Array
        SymbolTable.instance().lookup(self._state.last_function_name).args_type[-1] = IdType.Array

    @Symbols.symbol(ActionSymbol.DeclareFunction)
    def declare_function(self) -> None:
        """ Declares a function. """
        self._state.data_pointer = self._state.data_address
        self._state.temp_pointer = self._state.temp_address
        self._state.last_function_name = self._state.last_id.lexeme

        if self._state.set_exec:
            self._pb.i -= 1

        id_ = SymbolTable.instance().lookup(self._state.last_id.lexeme)
        id_.type, id_.return_type = IdType.Function, id_.type
        id_.address = self._pb.i

        if not self._state.set_exec:
            self._state.set_exec = True
            self._pb.i -= 1
            function, description = self._ss.pop(return_description=True)
            self.hold() # jump to main before 1st function at #exec_main
            self._ss.push(function, description)

    @Symbols.symbol(ActionSymbol.CaptureParamType)
    def capture_param_type(self) -> None:
        """ Counts the parameters of the function. """
        SymbolTable.instance().lookup(self._state.last_function_name).args_type.append(self._state.last_type)

    @Symbols.symbol(ActionSymbol.DeclareId)
    def declare_id(self, token: Token) -> None:
        """ Declares an id (variable, argument, or function).

        Args:
            token (Token): Id token.
        """
        id_ = SymbolTable.instance().lookup(token.lexeme)
        id_.address = self._state.getvar()
        id_.type = self._state.last_type
        self._state.last_id = token

        if self._state.declaring_args:
            self._as.pop(Value.direct(id_.address))
        else:
            self._pb.append(Instruction(Operation.Assign,
                            Value.immediate(0),
                            Value.direct(id_.address)))

    @Symbols.symbol(ActionSymbol.Declare)
    def declare(self) -> None:
        """ Enable declaring mode. """
        SymbolTable.instance().declaring = True

    @Symbols.symbol(ActionSymbol.Assign)
    def assign(self) -> None:
        """ Assigns the value from the semantic stack to the id. """
        self._pb.append(Instruction(Operation.Assign,
                        self._ss.pop(),
                        self._ss.from_top()))

    @Symbols.symbol(ActionSymbol.OpExec)
    def op_exec(self, token: Token) -> None:
        """ Executes the operation from the semantic stack. """
        arg2 = self._ss.pop()
        op: Operation = self._ss.pop()
        arg1 = self._ss.pop()
        for arg in [arg1, arg2]:
            if arg.type not in [IdType.Int, IdType.NotSpecified]:
                CodeGenErrorLogger.instance.log(
                    token.lineno, f"Type mismatch in operands, Got {arg.type.value} instead of int.")            
        t = Value.direct(self._state.gettemp(), IdType.Int)
        self._pb.append(Instruction(op, arg1, arg2, t))
        self._ss.push(t, f'op_exec {op}')

    @Symbols.symbol(ActionSymbol.OpPush)
    def op_push(self, token: Token) -> None:
        """ Pushes the operator to the semantic stack.

        Args:
            token (Token): Operator symbol token.
        """
        self._ss.push(Operation.from_symbol(token.lexeme), f'op_push {token.lexeme}')

    @Symbols.symbol(ActionSymbol.Hold)
    def hold(self) -> None:
        """ Pushes the current program counter to the semantic stack
        and skips the next instruction. """
        self.label()
        self._pb.i += 1

    @Symbols.symbol(ActionSymbol.Label)
    def label(self) -> None:
        """ Pushes the current program counter to the semantic stack. """
        self._ss.push(Value.direct(self._pb.i), 'label')

    @Symbols.symbol(ActionSymbol.Decide)
    def decide(self) -> None:
        """ Conditional jump from the holden line to the current line. """
        holden_line = self._ss.pop().value
        condition = self._ss.pop()
        target = Value.direct(self._pb.i)
        self._pb[holden_line] = Instruction(Operation.Jpf, condition, target)

    @Symbols.symbol(ActionSymbol.JpfRepeat)
    def jpf_repeat(self) -> None:
        """ Unconditional jump to the holden line, for repeat-until. """
        condition = self._ss.pop()
        label = self._ss.pop()
        self._pb.append(Instruction(Operation.Jpf, condition, label))

    @Symbols.symbol(ActionSymbol.FunctionCall)
    def function_call(self, token: Token) -> None:
        """ Calls a function. 
        1. Stores the current frame data and registers.
        2. Pushes the arguments to the stack.
        3. Assigns the ra register.
        4. Jumps to the function.
        5. Restores the frame data and registers.
        6. Collects the return value.

        Args:
            token (Token): Function call token.
        """
        self.store()
        args_type = self.push_args()
        instno = self._ss.pop()
        fid = SymbolTable.instance().lookup_by_instno(instno.value)
        if len(args_type) != len(fid.args_type):
            CodeGenErrorLogger.instance.log(
                token.lineno, f"Mismatch in numbers of arguments of '{fid.lexeme}'.")
        arglen = min(len(args_type), len(fid.args_type))
        for i, (actual_type, expected_type) in enumerate(zip(args_type[:arglen], fid.args_type[:arglen])):
            if actual_type not in [expected_type, IdType.NotSpecified]:
                CodeGenErrorLogger.instance.log(
                    token.lineno, f"Mismatch in type of argument "
                    f"{i + 1} of '{fid.lexeme}'. Expected '{expected_type.value}' but "
                    f"got '{actual_type.value}' instead.")
        self._pb.append(Instruction(Operation.Assign,
                        Value.immediate(self._pb.i + 2),
                        Value.direct(self._rf.ra)))
        self._pb.append(Instruction(Operation.Jp, instno))
        self.restore()
        self.collect(fid.return_type)

    def store(self) -> None:
        """ Stores the current frame data and registers. """
        for address in range(self._state.data_pointer, self._state.data_address, self._config.word_size.value):
            self._as.push(Value.direct(address))
        for address in range(self._state.temp_pointer, self._state.temp_address, self._config.word_size.value):
            self._as.push(Value.direct(address))
        self._as.push_rf()

    def push_args(self) -> List[IdType]:
        """ Pushes the arguments to the stack. """
        args_type = []
        for _ in range(self._ss.length - self._state.arg_pointer.pop()):
            arg = self._ss.pop()
            args_type.append(arg.type)
            self._as.push(arg)
        return args_type[::-1]

    def restore(self) -> None:
        """ Restores the frame data and registers. """
        self._as.pop_rf()
        for address in range(self._state.temp_address, self._state.temp_pointer, -self._config.word_size.value):
            self._as.pop(Value.direct(address - self._config.word_size.value))
        for address in range(self._state.data_address, self._state.data_pointer, -self._config.word_size.value):
            self._as.pop(Value.direct(address - self._config.word_size.value))

    def collect(self, return_type: IdType) -> None:
        """ Collects the return value. """
        t = Value.direct(self._state.gettemp(), return_type)
        self._pb.append(Instruction(Operation.Assign,
                        Value.direct(self._rf.rv), t))
        self._ss.push(t, 'collect')

    @Symbols.symbol(ActionSymbol.FunctionReturn)
    def function_return(self) -> None:
        """ Returns from a function. """
        self._pb.append(Instruction(Operation.Jp, Value.indirect(self._rf.ra)))

    @Symbols.symbol(ActionSymbol.ArgInit)
    def arg_init(self) -> None:
        """ Enables argument declaraing mode. """
        self._state.declaring_args = True

    @Symbols.symbol(ActionSymbol.ArgFinish)
    def arg_finish(self) -> None:
        """ Disables argument declaraing mode. """
        self._state.declaring_args = False

    @Symbols.symbol(ActionSymbol.ArgPass)
    def arg_pass(self) -> None:
        """ Stores the first argument pointer in the semantic stack. """
        self._state.arg_pointer.append(self._ss.length)

    @Symbols.symbol(ActionSymbol.FunctionScope)
    def function_scope(self) -> None:
        """ Pushes a function scope. """
        self._scope.push_type(ScopeType.Function)

    @Symbols.symbol(ActionSymbol.ContainerScope)
    def container_scope(self) -> None:
        """ Pushes a container scope. """
        self._scope.push_type(ScopeType.Container)

    @Symbols.symbol(ActionSymbol.TemporaryScope)
    def temporary_scope(self) -> None:
        """ Pushes a temporary scope. """
        self._scope.push_type(ScopeType.Temporary)

    @Symbols.symbol(ActionSymbol.SimpleScope)
    def simple_scope(self) -> None:
        """ Pushes a simple scope. """
        self._scope.push_type(ScopeType.Simple)

    @Symbols.symbol(ActionSymbol.ScopeStart)
    def scope_start(self) -> None:
        """ Starts the pushed scope type. """
        SymbolTable.instance().create_scope()
        self._scope.create_scope()

    @Symbols.symbol(ActionSymbol.ScopeEnd)
    def scope_end(self) -> None:
        """ Ends the incoming scope type. """
        SymbolTable.instance().delete_scope()
        self._scope.delete_scope()

    @Symbols.symbol(ActionSymbol.Prison)
    def prison(self) -> None:
        """ Moves the current program counter to the jail. """
        self._scope.prison()

    @Symbols.symbol(ActionSymbol.PrisonBreak)
    def prison_break(self) -> None:
        """ Breaks the jail. """
        self._scope.prison_break()

    @Symbols.symbol(ActionSymbol.ExecMain)
    def exec_main(self) -> None:
        """ Jumps from the reserved line at #declare_function to the main function. """
        id_ = SymbolTable.instance().lookup('main')
        line = self._ss.pop().value
        self._pb[line] = Instruction(Operation.Jp, Value.direct(id_.address))

    @Symbols.symbol(ActionSymbol.SetMainRa)
    def set_main_ra(self) -> None:
        """ Sets the return address of the main function at the reserved line at #init_rf. """
        line = self._ss.pop().value
        self._pb[line] = Instruction(Operation.Assign,
                                     Value.immediate(self._pb.i),
                                     Value.direct(self._rf.ra))

    @Symbols.symbol(ActionSymbol.CheckInContainer)
    def check_in_container(self, token: Token) -> None:
        """ Checks if the current scope is a container.
        
        Args:
            token (Token): The token.
        """
        if not self._scope.are_we_inside(ScopeType.Container):
            CodeGenErrorLogger.instance.log(token.lineno, f"No 'repeat ... until' found for 'break'.")
