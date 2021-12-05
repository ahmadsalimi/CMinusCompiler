from dataclasses import dataclass, field
import re
from typing import Iterable, List, Tuple, Union

from ..scanner.scanner import Scanner, Token
from ..scanner.dfa import DFA, State, Transition, State, TokenType


@dataclass
class Node:
    name: Union[str, Token]
    children: List['Node'] = field(default_factory=list)


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

    def transition(self, token: Token) -> Tuple['State', Node, Token]:
        for transition in self.transitions:
            if isinstance(transition, TerminalTransition) and (r := transition.matches(token)) is not None:
                return transition.target, *r
            if isinstance(transition, NonTerminalTransition) and transition.dfa.in_first(token):
                m, token = transition.matches(token)
                assert m is not None, 'No match for token {}'.format(token) # TODO: proper error message
                return transition.target, m, token
        epsilon_transition = next((t for t in self.transitions if isinstance(t, EpsilonTransition)), None)
        assert epsilon_transition is not None, 'No epsilon transition for state {}'.format(self) # TODO: proper error message
        assert epsilon_transition.parent_dfa.in_follow(token), f'Token {token} not in follow of {epsilon_transition.parent_dfa}' # TODO: proper error message
        return epsilon_transition.target, 'epsilon', token


class TerminalTransition(Transition[Token]):
    def __init__(self, target: State, token_type: TokenType, pattern: str = r'.+') -> None:
        super().__init__(target)
        self.pattern = pattern
        self.token_type = token_type

    def matches(self, token: Token) -> Tuple[Node, Token]:
        if token.type == self.token_type and re.match(self.pattern, token.lexeme) is not None:
            return Node(token), Scanner.instance.get_next_token()
        return None


class NonTerminalTransition(Transition[Token]):
    def __init__(self, target: State, dfa: 'ParserDFA', name: str) -> None:
        super().__init__(target)
        self.name = name
        self.dfa = dfa

    def matches(self, token: Token) -> Tuple[Node, Token]:
        current_state = self.dfa.start_state
        tree = Node(self.name)
        while True:
            next_state, subtree, next_token = current_state.transition(token)
            tree.children.append(subtree)
            assert next_state is not None, 'No transition for token {}'.format(token) # TODO: proper error message

            if next_state.final:
                return tree, next_token
            
            current_state = next_state
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
