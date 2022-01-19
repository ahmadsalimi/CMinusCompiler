from dataclasses import dataclass, field
import re
from enum import Enum
from typing import Iterable, List, Tuple, Union
from anytree import Node as AnyNode

from .error_logger import ParserErrorLogger
from ..codegen.codegen import ActionSymbol, CodeGenerator, Symbols
from ..scanner.scanner import Scanner, Token
from ..scanner.dfa import DFA, State, Transition, State, TokenType


def format_nonterminal_name(snake_case: str) -> str:
    return snake_case.replace('_', '-').capitalize()


class ParserErrorType(Enum):
    IllegalToken = 1
    MissingNonTerminal = 2
    MissingTerminal = 3


class ParserError(Exception):
    def __init__(self, error_type: ParserErrorType) -> None:
        super().__init__()
        self.type = error_type


class UnexpectedEOF(Exception):
    def __init__(self, tree: 'Node') -> None:
        super().__init__()
        self.tree = tree


@dataclass
class Node:
    name: Union[str, Token]
    children: List['Node'] = field(default_factory=list)

    def __str__(self) -> str:
        return str(self.name)

    def to_anytree(self, parent: AnyNode = None) -> AnyNode:
        anynode = AnyNode(str(self), parent=parent)
        for child in self.children:
            child.to_anytree(parent=anynode)
        return anynode


class Matchable:
    def __init__(self, token_type: TokenType, pattern: str = r'.+'):
        self.token_type = token_type
        self.pattern = pattern

    def matches(self, token: Token) -> bool:
        return self.token_type == token.type and re.match(self.pattern, token.lexeme)


class EpsilonMatchable:
    pass


class ParserState(State[Token]):

    def __init__(self, id: int, final: bool = False):
        super().__init__(id)
        self.final = final


class ParserTransition(Transition[Token]):
    def __init__(self, target: State, symbols: List[ActionSymbol] = []) -> None:
        super().__init__(target)
        self.symbols = symbols

    def action(self, token: Token) -> None:
        for symbol in self.symbols:
            Symbols.symbols[symbol](CodeGenerator.instance, token)

class TerminalTransition(ParserTransition):
    def __init__(self, target: State, token_type: TokenType, value: str = None, symbols: List[ActionSymbol] = []) -> None:
        super().__init__(target, symbols=symbols)
        self.value = value
        self.token_type = token_type

    def matches(self, token: Token) -> Tuple[Node, Token]:
        if token.type == self.token_type and (self.value == token.lexeme or self.value is None):
            return Node(token), Scanner.instance.get_next_token()
        return None


class NonTerminalTransition(ParserTransition):
    def __init__(self, target: State, dfa: 'ParserDFA', name: str, symbols: List[ActionSymbol] = []) -> None:
        super().__init__(target, symbols=symbols)
        self.name = format_nonterminal_name(name)
        self.dfa = dfa

    def matches(self, token: Token) -> Tuple[Node, Token]:
        self.dfa.reset()
        tree = Node(self.name)
        while True:
            try:
                next_state, subtree, next_token = self.dfa.transition(token)
                tree.children.append(subtree)
            except UnexpectedEOF as e:
                tree.children.append(e.tree)
                e.tree = tree
                raise e
            except ParserError as e:
                if e.type == ParserErrorType.MissingTerminal:
                    next_state = self.dfa.current_state.transitions[0].target
                    next_token = token
                elif e.type == ParserErrorType.MissingNonTerminal:
                    nonterm_transition = next((t for t in self.dfa.current_state.transitions if isinstance(t, NonTerminalTransition)))
                    next_state = nonterm_transition.target
                    next_token = token
                else:
                    nonterm_transition = next((t for t in self.dfa.current_state.transitions if isinstance(t, NonTerminalTransition)))
                    while True:
                        token = Scanner.instance.get_next_token()
                        if nonterm_transition.dfa.in_first(token) or nonterm_transition.dfa.in_follow(token):
                            subtree, next_token = nonterm_transition.matches(token)
                            next_state = nonterm_transition.target
                            tree.children.append(subtree)
                            break
                        if token.type == TokenType.EOF:
                            ParserErrorLogger.instance.unexpected_eof(token.lineno)
                            raise UnexpectedEOF(tree)
                        ParserErrorLogger.instance.illegal_token(token)                        

            if next_state.final:
                return tree, next_token

            self.dfa.current_state = next_state
            token = next_token

class EpsilonTransition(ParserTransition):
    
    def __init__(self, target: State, parent_dfa: 'ParserDFA', symbols: List[ActionSymbol] = []) -> None:
        super().__init__(target, symbols=symbols)
        self.parent_dfa = parent_dfa

    def matches(self, token: Token) -> Tuple[Node, Token]:
        pass


class ParserDFA(DFA[Token]):
    def __init__(self, start_state: ParserState, name: str, first: Iterable[Matchable], follow: Iterable[Matchable]) -> None:
        super().__init__(start_state)
        self.start_state = start_state
        self.first = first
        self.follow = follow
        self.name = format_nonterminal_name(name)
        self.current_state = start_state

    def reset(self) -> None:
        self.current_state = self.start_state

    def transition(self, token: Token) -> Tuple['State', Node, Token]:
        for transition in self.current_state.transitions:
            if isinstance(transition, TerminalTransition) and (r := transition.matches(token)) is not None:
                transition.action(token)
                return transition.target, *r
            if isinstance(transition, NonTerminalTransition) and transition.dfa.in_first(token):
                transition.action(token)
                m, token = transition.matches(token)
                return transition.target, m, token
        epsilon_transition = next((t for t in self.current_state.transitions if isinstance(t, EpsilonTransition)), None)
        if epsilon_transition is None or not epsilon_transition.parent_dfa.in_follow(token): # syntax error
            if all(isinstance(transition, (TerminalTransition, EpsilonTransition)) for transition in self.current_state.transitions):
                error_lexeme = self.current_state.transitions[0].value \
                    or self.current_state.transitions[0].token_type.value
                ParserErrorLogger.instance.missing_token(token.lineno, error_lexeme)
                raise ParserError(ParserErrorType.MissingTerminal)

            nonterm_transition = next((t for t in self.current_state.transitions if isinstance(t, NonTerminalTransition)))
            if nonterm_transition.dfa.in_follow(token):
                ParserErrorLogger.instance.missing_token(token.lineno, nonterm_transition.name)
                raise ParserError(ParserErrorType.MissingNonTerminal)

            ParserErrorLogger.instance.illegal_token(token)
            raise ParserError(ParserErrorType.IllegalToken)

        epsilon_transition.action(token)
        return epsilon_transition.target, Node('epsilon'), token

    def in_first(self, token: Token) -> bool:
        m = self._in_set(self.first, token)
        if not m and any(isinstance(other_m, EpsilonMatchable) for other_m in self.first):
            return self.in_follow(token)
        return m

    def in_follow(self, token: Token) -> bool:
        return self._in_set(self.follow, token)

    @staticmethod
    def _in_set(the_set: Iterable[Matchable], token: Token) -> bool:
        return next((True for m in the_set if not isinstance(m, EpsilonMatchable) and m.matches(token)), False)
