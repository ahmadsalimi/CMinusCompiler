from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, List, Tuple, TypeVar, Union
from enum import Enum
import re


class TokenType(Enum):
    """
    TokenType class
    """
    ID = 'ID'
    KEYWORD = 'KEYWORD'
    SYMBOL = 'SYMBOL'
    NUM = 'NUM'
    COMMENT = 'COMMENT'
    WHITESPACE = 'WHITESPACE'
    EOF = '$'


TTransitionToken = TypeVar('TTransitionToken')


class State(Generic[TTransitionToken]):
    def __init__(self, id: int):
        self.id = id
        self.transitions: List['Transition[TTransitionToken]'] = []

    def add_transition(self, transition: 'Transition[TTransitionToken]'):
        self.transitions.append(transition)

    def transition(self, token: TTransitionToken) -> 'State':
        for t in self.transitions:
            if t.matches(token):
                return t.target


class FinalState(State[str]):
    def __init__(self, id: int, token_type_resolver: Callable[[str], TokenType]):
        super().__init__(id)
        self.resolve_token_type = token_type_resolver


class ErrorState(State[str]):

    def __init__(self, id: int, message):
        super().__init__(id)
        self.message = message


class Transition(ABC, Generic[TTransitionToken]):
    def __init__(self, target: State) -> None:
        self.target = target

    @abstractmethod
    def matches(self, token: TTransitionToken) -> bool:
        """ Return True if the transition matches the token

        Args:
            token (TTransitionToken): The token to check

        Returns:
            bool: True if the transition matches the token
        """


class RegexTransition(Transition[str]):
    def __init__(self, target: State, pattern: str):
        super().__init__(target)
        self.pattern = pattern

    def matches(self, char: str) -> bool:
        return re.match(self.pattern, char) is not None


class DFA(Generic[TTransitionToken]):

    def __init__(self, start_state: State[TTransitionToken]) -> None:
        self.start_state = start_state
        self.states = {start_state.id: start_state}

    def add_state(self, state: State[TTransitionToken]) -> None:
        self.states[state.id] = state

    def add_transition(self, source_id: int, transition: Transition[TTransitionToken]) -> None:
        self.states[source_id].add_transition(transition)
