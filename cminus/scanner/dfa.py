from typing import Callable, Dict, List
from enum import Enum
import re


class TokenType(Enum):
    """
    TokenType class
    """
    IDENTIFIER = 1
    KEYWORD = 2
    SYMBOL = 3
    NUMBER = 4
    COMMENT = 5
    WHITESPACE = 6


class State:
    def __init__(self, id: int):
        self.id = id
        self.transitions: List['Transition'] = []

    def add_transition(self, transition: 'Transition'):
        self.transitions.append(transition)

    def transition(self, char: str) -> 'State':
        for t in self.transitions:
            if t.matches(char):
                return t.target


class FinalState(State):
    def __init__(self, id: int, token_type_resolver: Callable[[str], TokenType]):
        super().__init__(id)
        self.resolve_token_type = token_type_resolver


class Transition:
    def __init__(self, target: State, pattern: str):
        self.target = target
        self.pattern = pattern

    def matches(self, char: str) -> bool:
        return re.match(self.pattern, char) is not None


class DFA:

    def __init__(self, start_state: State) -> None:
        self.start_state = start_state
        self.states = {start_state.id: start_state}

    def add_state(self, state: State) -> None:
        self.states[state.id] = state

    def add_transition(self, source_id: int, transition: Transition) -> None:
        self.states[source_id].add_transition(transition)
