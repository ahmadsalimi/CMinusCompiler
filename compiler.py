from dataclasses import dataclass, field
import os
from typing import Callable, Dict, Iterable, List

from anytree import RenderTree
from cminus.codegen.codegen import ActionSymbol, CodeGenerator
from cminus.codegen.config import CodeGenConfig
from cminus.codegen.error_logger import CodeGenErrorLogger
from cminus.parser.error_logger import ParserErrorLogger
from cminus.scanner.dfa import DFA, ErrorState, State, FinalState, RegexTransition, TokenType
from cminus.scanner.scanner import Scanner
from cminus.parser.dfa import EpsilonMatchable, EpsilonTransition, Matchable, NonTerminalTransition, ParserDFA, ParserState, TerminalTransition, UnexpectedEOF
from cminus.scanner.symbol_table import KEYWORDS


@dataclass
class TransitionInfo:
    source: int
    target: int


@dataclass
class TerminalTransitionInfo(TransitionInfo):
    token_type: TokenType
    value: str = None
    symbols: List[ActionSymbol] = field(default_factory=list)


@dataclass
class NonTerminalTransitionInfo(TransitionInfo):
    name: str
    symbols: List[ActionSymbol] = field(default_factory=list)


@dataclass
class EpsilonTransitionInfo(TransitionInfo):
    symbols: List[ActionSymbol] = field(default_factory=list)


@dataclass
class ParserDFAInfo:
    num_states: int
    final_state: int
    first: Iterable[Matchable] = field(default_factory=list)
    follow: Iterable[Matchable] = field(default_factory=list)
    terminal_transitions: List[TerminalTransitionInfo] = field(default_factory=list)
    non_terminal_transitions: List[NonTerminalTransitionInfo] = field(default_factory=list)
    epsilon_transitions: List[EpsilonTransitionInfo] = field(default_factory=list)


def create_transition_diagrams() -> ParserDFA:
    infos: Dict[str, ParserDFAInfo] = dict(
        program=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(2, 3, TokenType.EOF,
                                       symbols=[ActionSymbol.ExecMain,
                                                ActionSymbol.SetMainRa]),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'declaration_list',
                                          symbols=[ActionSymbol.Hold,
                                                   ActionSymbol.Output,
                                                   ActionSymbol.JpFrom,
                                                   ActionSymbol.InitRf]),
            ]
        ),
        declaration_list=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            follow=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.SYMBOL, r'(;|\(|{|})'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'declaration'),
                NonTerminalTransitionInfo(2, 3, 'declaration_list'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 3),
            ]
        ),
        declaration=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            follow=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.SYMBOL, r'(;|\(|{|})'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|int|void)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'declaration_initial',
                                          symbols=[ActionSymbol.Declare]),
                NonTerminalTransitionInfo(2, 3, 'declaration_prime'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(3, 4, symbols=[ActionSymbol.Pop]),
            ]
        ),
        declaration_initial=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\(|\)|\[|;|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'type_specifier',
                                          symbols=[ActionSymbol.Ptype]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(2, 3, TokenType.ID,
                                       symbols=[ActionSymbol.DeclareId,
                                                ActionSymbol.Pid]),
            ],
        ),
        declaration_prime=ParserDFAInfo(
            num_states=2,
            final_state=2,
            first=[
                Matchable(TokenType.SYMBOL, r'(\(|\[|;)'),
            ],
            follow=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.SYMBOL, r'(;|\(|{|})'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|int|void)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'fun_declaration_prime'),
                NonTerminalTransitionInfo(1, 2, 'var_declaration_prime',
                                          symbols=[ActionSymbol.CheckDeclarationType]),
            ],
        ),
        var_declaration_prime=ParserDFAInfo(
            num_states=5,
            final_state=5,
            first=[
                Matchable(TokenType.SYMBOL, r'(;|\[)'),
            ],
            follow=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.SYMBOL, r'(;|\(|{|})'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|int|void)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '['),
                TerminalTransitionInfo(2, 3, TokenType.NUM,
                                       symbols=[ActionSymbol.Pnum]),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ']'),
                TerminalTransitionInfo(4, 5, TokenType.SYMBOL, ';',
                                       symbols=[ActionSymbol.DeclareArray]),
                TerminalTransitionInfo(1, 5, TokenType.SYMBOL, ';'),
            ],
        ),
        fun_declaration_prime=ParserDFAInfo(
            num_states=6,
            final_state=6,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
            ],
            follow=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.SYMBOL, r'(;|\(|{|})'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|int|void)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'params'),
                NonTerminalTransitionInfo(4, 5, 'compound_stmt'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '(',
                                       symbols=[ActionSymbol.DeclareFunction,
                                                ActionSymbol.TemporaryScope,
                                                ActionSymbol.ScopeStart,
                                                ActionSymbol.ArgInit]),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ')',
                                       symbols=[ActionSymbol.ArgFinish,
                                                ActionSymbol.FunctionScope,
                                                ActionSymbol.ScopeStart]),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(5, 6, symbols=[ActionSymbol.ScopeEnd,
                                                     ActionSymbol.FunctionScope,
                                                     ActionSymbol.ScopeEnd,
                                                     ActionSymbol.TemporaryScope,
                                                     ActionSymbol.FunctionReturn]),
            ],
        ),
        type_specifier=ParserDFAInfo(
            num_states=2,
            final_state=2,
            first=[
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            follow=[
                Matchable(TokenType.ID),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'int'),
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'void'),
            ],
        ),
        params=ParserDFAInfo(
            num_states=5,
            final_state=5,
            first=[
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(3, 4, 'param_prime'),
                NonTerminalTransitionInfo(4, 5, 'param_list', symbols=[ActionSymbol.Pop]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'int',
                                       symbols=[ActionSymbol.Declare,
                                                ActionSymbol.Ptype,
                                                ActionSymbol.CaptureParamType]),
                TerminalTransitionInfo(2, 3, TokenType.ID,
                                       symbols=[ActionSymbol.DeclareId,
                                                ActionSymbol.Pid]),
                TerminalTransitionInfo(1, 5, TokenType.KEYWORD, 'void'),
            ],
        ),
        param_list=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r','),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'param'),
                NonTerminalTransitionInfo(3, 4, 'param_list'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, ','),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 4),
            ],
        ),
        param=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                Matchable(TokenType.KEYWORD, r'(int|void)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(,|\))'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'declaration_initial',
                                          symbols=[ActionSymbol.Declare,
                                                   ActionSymbol.CaptureParamType]),
                NonTerminalTransitionInfo(2, 3, 'param_prime',
                                          symbols=[ActionSymbol.CheckDeclarationType]),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(3, 4, symbols=[ActionSymbol.Pop]),
            ],
        ),
        param_prime=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'\['),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(,|\))'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '[',
                                       symbols=[ActionSymbol.ArrayType]),
                TerminalTransitionInfo(2, 3, TokenType.SYMBOL, ']'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 3),
            ],
        ),
        compound_stmt=ParserDFAInfo(
            num_states=5,
            final_state=5,
            first=[
                Matchable(TokenType.SYMBOL, r'{'),
            ],
            follow=[
                Matchable(TokenType.EOF),
                Matchable(TokenType.SYMBOL, r'(;|\(|{|})'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|int|void|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'declaration_list'),
                NonTerminalTransitionInfo(3, 4, 'statement_list'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '{'),
                TerminalTransitionInfo(4, 5, TokenType.SYMBOL, '}'),
            ],
        ),
        statement_list=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'({|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'}'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'statement'),
                NonTerminalTransitionInfo(2, 3, 'statement_list'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 3),
            ],
        ),
        statement=ParserDFAInfo(
            num_states=2,
            final_state=2,
            first=[
                Matchable(TokenType.SYMBOL, r'({|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'expression_stmt'),
                NonTerminalTransitionInfo(1, 2, 'compound_stmt'),
                NonTerminalTransitionInfo(1, 2, 'selection_stmt'),
                NonTerminalTransitionInfo(1, 2, 'iteration_stmt'),
                NonTerminalTransitionInfo(1, 2, 'return_stmt'),
            ],
        ),
        expression_stmt=ParserDFAInfo(
            num_states=4,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'(\(|;)'),
                Matchable(TokenType.KEYWORD, r'break'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'expression'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(2, 3, TokenType.SYMBOL, ';',
                                       symbols=[ActionSymbol.Pop]),
                TerminalTransitionInfo(1, 4, TokenType.KEYWORD, 'break',
                                       symbols=[ActionSymbol.CheckInContainer]),
                TerminalTransitionInfo(4, 3, TokenType.SYMBOL, ';',
                                       symbols=[ActionSymbol.ContainerScope,
                                                ActionSymbol.Prison]),
                TerminalTransitionInfo(1, 3, TokenType.SYMBOL, ';'),
            ],
        ),
        selection_stmt=ParserDFAInfo(
            num_states=7,
            final_state=7,
            first=[
                Matchable(TokenType.KEYWORD, r'if'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(3, 4, 'expression'),
                NonTerminalTransitionInfo(5, 6, 'statement',
                                          symbols=[ActionSymbol.Hold,
                                                   ActionSymbol.SimpleScope,
                                                   ActionSymbol.ScopeStart]),
                NonTerminalTransitionInfo(6, 7, 'else_stmt',
                                          symbols=[ActionSymbol.ScopeEnd,
                                                   ActionSymbol.SimpleScope]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'if'),
                TerminalTransitionInfo(2, 3, TokenType.SYMBOL, '('),
                TerminalTransitionInfo(4, 5, TokenType.SYMBOL, ')'),
            ],
        ),
        else_stmt=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                Matchable(TokenType.KEYWORD, r'(else|endif)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'statement',
                                          symbols=[ActionSymbol.SimpleScope,
                                                   ActionSymbol.ScopeStart]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'else',
                                       symbols=[ActionSymbol.TemporaryScope,
                                                ActionSymbol.Prison,
                                                ActionSymbol.Decide]),
                TerminalTransitionInfo(3, 4, TokenType.KEYWORD, 'endif',
                                       symbols=[ActionSymbol.ScopeEnd,
                                                ActionSymbol.SimpleScope,
                                                ActionSymbol.TemporaryScope,
                                                ActionSymbol.PrisonBreak]),
                TerminalTransitionInfo(1, 4, TokenType.KEYWORD, 'endif',
                                       symbols=[ActionSymbol.Decide]),
            ],
        ),
        iteration_stmt=ParserDFAInfo(
            num_states=7,
            final_state=7,
            first=[
                Matchable(TokenType.KEYWORD, r'repeat'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'statement',
                                          symbols=[ActionSymbol.Label,
                                                   ActionSymbol.ContainerScope,
                                                   ActionSymbol.ScopeStart]),
                NonTerminalTransitionInfo(5, 6, 'expression'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'repeat'),
                TerminalTransitionInfo(3, 4, TokenType.KEYWORD, 'until'),
                TerminalTransitionInfo(4, 5, TokenType.SYMBOL, '('),
                TerminalTransitionInfo(6, 7, TokenType.SYMBOL, ')',
                                       symbols=[ActionSymbol.JpfRepeat,
                                                ActionSymbol.ScopeEnd,
                                                ActionSymbol.ContainerScope]),
            ],
        ),
        return_stmt=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                Matchable(TokenType.KEYWORD, r'return'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'return_stmt_prime'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.KEYWORD, 'return'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(3, 4, symbols=[ActionSymbol.FunctionScope,
                                                     ActionSymbol.Prison]),
            ],
        ),
        return_stmt_prime=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'(\(|;)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'({|}|\(|;)'),
                Matchable(TokenType.KEYWORD, r'(break|if|repeat|return|endif|else|until)'),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'expression',
                                          symbols=[ActionSymbol.Prv]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(2, 3, TokenType.SYMBOL, ';',
                                       symbols=[ActionSymbol.Assign,
                                                ActionSymbol.Pop]),
                TerminalTransitionInfo(1, 3, TokenType.SYMBOL, ';'),
            ],
        ),
        expression=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'B'),
                NonTerminalTransitionInfo(1, 3, 'simple_expression_zegond'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.ID,
                                       symbols=[ActionSymbol.Pid]),
            ],
        ),
        B=ParserDFAInfo(
            num_states=7,
            final_state=5,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(\[|=|\(|\*|\+|-|<|==)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'expression'),
                NonTerminalTransitionInfo(4, 5, 'H',
                                          symbols=[ActionSymbol.Parray]),
                NonTerminalTransitionInfo(6, 7, 'expression'),
                NonTerminalTransitionInfo(1, 5, 'simple_expression_prime'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '['),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ']'),
                TerminalTransitionInfo(1, 6, TokenType.SYMBOL, '='),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(7, 5, symbols=[ActionSymbol.Assign]),
            ],
        ),
        H=ParserDFAInfo(
            num_states=6,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(=|\*|\+|-|<|==)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'G'),
                NonTerminalTransitionInfo(2, 3, 'D'),
                NonTerminalTransitionInfo(3, 4, 'C'),
                NonTerminalTransitionInfo(5, 6, 'expression'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 5, TokenType.SYMBOL, '='),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(6, 4, symbols=[ActionSymbol.Assign]),
            ],
        ),
        simple_expression_zegond=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'additive_expression_zegond'),
                NonTerminalTransitionInfo(2, 3, 'C'),
            ],
        ),
        simple_expression_prime=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(\(|\*|\+|-|<|==)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'additive_expression_prime'),
                NonTerminalTransitionInfo(2, 3, 'C'),
            ],
        ),
        C=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(<|==)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'relop'),
                NonTerminalTransitionInfo(2, 3, 'additive_expression'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(3, 4, symbols=[ActionSymbol.OpExec]),
                EpsilonTransitionInfo(1, 4),
            ],
        ),
        relop=ParserDFAInfo(
            num_states=2,
            final_state=2,
            first=[
                Matchable(TokenType.SYMBOL, r'(<|==)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '<',
                                       symbols=[ActionSymbol.OpPush]),
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '==',
                                       symbols=[ActionSymbol.OpPush]),
            ],
        ),
        additive_expression=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'term'),
                NonTerminalTransitionInfo(2, 3, 'D'),
            ],
        ),
        additive_expression_prime=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(\(|\*|\+|-)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(<|==|;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'term_prime'),
                NonTerminalTransitionInfo(2, 3, 'D'),
            ],
        ),
        additive_expression_zegond=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(<|==|;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'term_zegond'),
                NonTerminalTransitionInfo(2, 3, 'D'),
            ],
        ),
        D=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(\+|-)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(<|==|;|\)|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'addop'),
                NonTerminalTransitionInfo(2, 3, 'term'),
                NonTerminalTransitionInfo(3, 4, 'D', symbols=[ActionSymbol.OpExec]),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 4),
            ],
        ),
        addop=ParserDFAInfo(
            num_states=2,
            final_state=2,
            first=[
                Matchable(TokenType.SYMBOL, r'(\+|-)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '+',
                                       symbols=[ActionSymbol.OpPush]),
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '-',
                                       symbols=[ActionSymbol.OpPush]),
            ],
        ),
        term=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'factor'),
                NonTerminalTransitionInfo(2, 3, 'G'),
            ],
        ),
        term_prime=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(\*|\()'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'factor_prime'),
                NonTerminalTransitionInfo(2, 3, 'G'),
            ],
        ),
        term_zegond=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'factor_zegond'),
                NonTerminalTransitionInfo(2, 3, 'G'),
            ],
        ),
        G=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'\*'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'factor'),
                NonTerminalTransitionInfo(3, 4, 'G',
                                          symbols=[ActionSymbol.OpExec]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '*',
                                       symbols=[ActionSymbol.OpPush]),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 4),
            ],
        ),
        factor=ParserDFAInfo(
            num_states=5,
            final_state=4,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,|\*)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'expression'),
                NonTerminalTransitionInfo(5, 4, 'var_call_prime'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '('),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ')'),
                TerminalTransitionInfo(1, 5, TokenType.ID, symbols=[ActionSymbol.Pid]),
                TerminalTransitionInfo(1, 4, TokenType.NUM, symbols=[ActionSymbol.Pnum]),
            ],
        ),
        var_call_prime=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'(\(|\[)'),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,|\*)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'args', symbols=[ActionSymbol.ArgPass]),
                NonTerminalTransitionInfo(1, 4, 'var_prime'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '('),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ')',
                                       symbols=[ActionSymbol.FunctionCall]),
            ],
        ),
        var_prime=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'\['),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,|\*)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'expression'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '['),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ']',
                                       symbols=[ActionSymbol.Parray]),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 4),
            ],
        ),
        factor_prime=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'\('),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,|\*)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'args',
                                          symbols=[ActionSymbol.ArgPass]),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '('),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ')',
                                       symbols=[ActionSymbol.FunctionCall]),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 4),
            ],
        ),
        factor_zegond=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'(\+|-|;|\)|<|==|\]|,|\*)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'expression'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, '('),
                TerminalTransitionInfo(3, 4, TokenType.SYMBOL, ')'),
                TerminalTransitionInfo(1, 4, TokenType.NUM,
                                       symbols=[ActionSymbol.Pnum]),
            ],
        ),
        args=ParserDFAInfo(
            num_states=2,
            final_state=2,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'arg_list'),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 2),
            ],
        ),
        arg_list=ParserDFAInfo(
            num_states=3,
            final_state=3,
            first=[
                Matchable(TokenType.SYMBOL, r'\('),
                Matchable(TokenType.ID),
                Matchable(TokenType.NUM),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(1, 2, 'expression'),
                NonTerminalTransitionInfo(2, 3, 'arg_list_prime'),
            ],
        ),
        arg_list_prime=ParserDFAInfo(
            num_states=4,
            final_state=4,
            first=[
                EpsilonMatchable(),
                Matchable(TokenType.SYMBOL, r','),
            ],
            follow=[
                Matchable(TokenType.SYMBOL, r'\)'),
            ],
            non_terminal_transitions=[
                NonTerminalTransitionInfo(2, 3, 'expression'),
                NonTerminalTransitionInfo(3, 4, 'arg_list_prime'),
            ],
            terminal_transitions=[
                TerminalTransitionInfo(1, 2, TokenType.SYMBOL, ','),
            ],
            epsilon_transitions=[
                EpsilonTransitionInfo(1, 4),
            ],
        ),
    )

    dfas = {
        name: ParserDFA(ParserState(1), name, info.first, info.follow)
        for name, info in infos.items()
    }

    for name, info in infos.items():
        dfa = dfas[name]
        for i in range(2, info.num_states + 1):
            dfa.add_state(ParserState(i, final=i == info.final_state))

        for transition in info.terminal_transitions:
            dfa.add_transition(
                transition.source,
                TerminalTransition(
                    dfa.states[transition.target],
                    transition.token_type,
                    value=transition.value,
                    symbols=transition.symbols,
                )
            )

        for transition in info.non_terminal_transitions:
            dfa.add_transition(
                transition.source,
                NonTerminalTransition(
                    dfa.states[transition.target],
                    dfas[transition.name],
                    transition.name,
                    symbols=transition.symbols,
                )
            )

        for transition in info.epsilon_transitions:
            dfa.add_transition(
                transition.source,
                EpsilonTransition(
                    dfa.states[transition.target],
                    dfa,
                    symbols=transition.symbols,
                )
            )

    return dfas['program']

def create_cminus_dfa() -> DFA:
    dfa = DFA(State(1))
    
    def default_resolver(token_type: TokenType) -> Callable[[str], TokenType]:
        return lambda _: token_type

    finals = {
        2: default_resolver(TokenType.NUM),
        3: lambda token: TokenType.KEYWORD if token in KEYWORDS else TokenType.ID,
        4: default_resolver(TokenType.SYMBOL),
        5: default_resolver(TokenType.SYMBOL),
        8: default_resolver(TokenType.COMMENT),
        11: default_resolver(TokenType.WHITESPACE),
        13: default_resolver(TokenType.SYMBOL),
    }
    error_states = {
        12: 'Invalid number',
        14: 'Unmatched comment',
        15: 'Invalid input',
    }
    for i in range(2, 16):
        if i in finals:
            dfa.add_state(FinalState(i, finals[i]))
        elif i in error_states:
            dfa.add_state(ErrorState(i, error_states[i]))
        else:
            dfa.add_state(State(i))

    ILLEGAL_CHARS = r'[^a-zA-Z0-9;:,\[\]\(\)\{\}\+\-<=\*/\s]'

    dfa.add_transition(1, RegexTransition(dfa.states[2], r'\d'))
    dfa.add_transition(2, RegexTransition(dfa.states[2], r'\d'))
    dfa.add_transition(2, RegexTransition(dfa.states[12], r'([a-zA-Z]|' + ILLEGAL_CHARS + r')'))

    dfa.add_transition(1, RegexTransition(dfa.states[3], r'[a-zA-Z]'))
    dfa.add_transition(3, RegexTransition(dfa.states[3], r'[a-zA-Z0-9]'))
    dfa.add_transition(3, RegexTransition(dfa.states[15], ILLEGAL_CHARS))

    dfa.add_transition(1, RegexTransition(dfa.states[4], r'[;:,\[\]\(\)\{\}\+\-<]'))
    dfa.add_transition(1, RegexTransition(dfa.states[5], r'='))
    dfa.add_transition(5, RegexTransition(dfa.states[4], r'='))
    dfa.add_transition(1, RegexTransition(dfa.states[13], r'\*'))
    dfa.add_transition(13, RegexTransition(dfa.states[14], r'/'))
    dfa.add_transition(13, RegexTransition(dfa.states[15], ILLEGAL_CHARS))
    dfa.add_transition(5, RegexTransition(dfa.states[15], ILLEGAL_CHARS))

    dfa.add_transition(1, RegexTransition(dfa.states[6], r'/'))
    dfa.add_transition(6, RegexTransition(dfa.states[7], r'/'))
    dfa.add_transition(7, RegexTransition(dfa.states[7], r'[^\n]'))
    dfa.add_transition(7, RegexTransition(dfa.states[8], r'\n'))
    dfa.add_transition(6, RegexTransition(dfa.states[9], r'\*'))
    dfa.add_transition(9, RegexTransition(dfa.states[9], r'[^\*]'))
    dfa.add_transition(9, RegexTransition(dfa.states[10], r'\*'))
    dfa.add_transition(10, RegexTransition(dfa.states[9], r'[^\*/]'))
    dfa.add_transition(10, RegexTransition(dfa.states[10], r'\*'))
    dfa.add_transition(10, RegexTransition(dfa.states[8], r'/'))
    dfa.add_transition(6, RegexTransition(dfa.states[15], ILLEGAL_CHARS))

    dfa.add_transition(1, RegexTransition(dfa.states[11], r'\s'))

    dfa.add_transition(1, RegexTransition(dfa.states[15], ILLEGAL_CHARS))

    return dfa


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Cminus Parser')
    parser.add_argument('-i', '--input', default='input.txt', help='Input file')
    parser.add_argument('-o', '--output-directory', default='', help='Output directory')

    args = parser.parse_args()

    with open(args.input, 'r') as f:
        code = f.read()

    dfa = create_cminus_dfa()
    scanner = Scanner(dfa, code, [9, 10])
    parser = create_transition_diagrams()
    program = NonTerminalTransition(None, parser, 'program')

    with CodeGenErrorLogger(os.path.join(args.output_directory, 'semantic_errors.txt')):
        codegen = CodeGenerator(CodeGenConfig())

        token = scanner.get_next_token()
        with ParserErrorLogger(os.path.join(args.output_directory, 'syntax_errors.txt')):
            try:
                tree, _ = program.matches(token)
            except UnexpectedEOF as e:
                tree = e.tree

    anytree = tree.to_anytree()
    with open(os.path.join(args.output_directory, 'parse_tree.txt'), 'w') as f:
        for pre, _, node in RenderTree(anytree):
            print(f'{pre}{node.name}', file=f)

    if not CodeGenErrorLogger.instance.any_error:
        with open(os.path.join(args.output_directory, 'output.txt'), 'w') as f:
            print(codegen.export(), file=f)
