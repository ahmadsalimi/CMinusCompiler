from dataclasses import dataclass, field
import re
from enum import Enum
from typing import Iterable, List, Tuple, Union

from ..scanner.scanner import Scanner, Token
from ..scanner.dfa import DFA, State, Transition, State, TokenType


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

    def __repr__(self) -> str:
        return repr(self.name)


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


class TerminalTransition(Transition[Token]):
    def __init__(self, target: State, token_type: TokenType, value: str = None) -> None:
        super().__init__(target)
        self.value = value
        self.token_type = token_type

    def matches(self, token: Token) -> Tuple[Node, Token]:
        if token.type == self.token_type and (self.value == token.lexeme or self.value is None):
            return Node(token), Scanner.instance.get_next_token()
        return None


class NonTerminalTransition(Transition[Token]):
    def __init__(self, target: State, dfa: 'ParserDFA', name: str) -> None:
        super().__init__(target)
        self.name = name
        self.dfa = dfa

    def matches(self, token: Token) -> Tuple[Node, Token]:
        self.dfa.reset()
        tree = Node(self.name)
        while True:
            try:
                next_state, subtree, next_token = self.dfa.transition(token)
                tree.children.append(subtree)
            except UnexpectedEOF as e:
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
                            break
                        if token.type == TokenType.EOF:
                            # call error logger: unexpected EOF
                            print(f'#{token.lineno}: Unexpected EOF')
                            raise UnexpectedEOF(tree)
                        # call error logger: illegal token
                        print(f'#{token.lineno}: Illegal {token.lexeme if token.type not in [TokenType.ID, TokenType.NUM] else token.type.name}')

            if next_state.final:
                return tree, next_token

            self.dfa.current_state = next_state
            token = next_token

class EpsilonTransition(Transition[Token]):
    
    def __init__(self, target: State, parent_dfa: 'ParserDFA') -> None:
        super().__init__(target)
        self.parent_dfa = parent_dfa

    def matches(self, token: Token) -> Tuple[Node, Token]:
        pass


class ParserDFA(DFA[Token]):
    def __init__(self, start_state: ParserState, name: str, first: Iterable[Matchable], follow: Iterable[Matchable]) -> None:
        super().__init__(start_state)
        self.start_state = start_state
        self.first = first
        self.follow = follow
        self.name = name
        self.current_state = start_state

    def reset(self) -> None:
        self.current_state = self.start_state

    def transition(self, token: Token) -> Tuple['State', Node, Token]:
        for transition in self.current_state.transitions:
            if isinstance(transition, TerminalTransition) and (r := transition.matches(token)) is not None:
                return transition.target, *r
            if isinstance(transition, NonTerminalTransition) and transition.dfa.in_first(token):
                m, token = transition.matches(token)
                return transition.target, m, token
        epsilon_transition = next((t for t in self.current_state.transitions if isinstance(t, EpsilonTransition)), None)
        if epsilon_transition is None or not epsilon_transition.parent_dfa.in_follow(token): # syntax error
            if all(isinstance(transition, (TerminalTransition, EpsilonTransition)) for transition in self.current_state.transitions):
                # Call the error logger: missing first transition.value
                print(f'#{token.lineno}: Missing {self.current_state.transitions[0].value or self.current_state.transitions[0].token_type.name}')
                raise ParserError(ParserErrorType.MissingTerminal)
            nonterm_transition = next((t for t in self.current_state.transitions if isinstance(t, NonTerminalTransition)))
            if nonterm_transition.dfa.in_follow(token):
                # Call the error logger: missing self.name
                print(f'#{token.lineno}: Missing {nonterm_transition.name}')
                raise ParserError(ParserErrorType.MissingNonTerminal)

            # Call the error logger: illegal token
            print(f'#{token.lineno}: Illegal {token.lexeme if token.type not in [TokenType.ID, TokenType.NUM] else token.type.name}')
            raise ParserError(ParserErrorType.IllegalToken)

        return epsilon_transition.target, 'epsilon', token

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
