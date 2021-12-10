from typing import List, Tuple
from collections import OrderedDict
from dataclasses import dataclass

from .dfa import DFA, ErrorState, FinalState, State, TokenType
from .error import ScannerError


KEYWORDS = [
    'if',
    'else',
    'endif',
    'void',
    'int',
    'repeat',
    'break',
    'until',
    'return'
]


@dataclass
class Token:
    type: TokenType
    lexeme: str
    lineno: int

    def __str__(self) -> str:
        if self.type == TokenType.EOF:
            return self.lexeme
        return f'({self.type.value}, {self.lexeme})'


class Scanner:
    instance: 'Scanner' = None

    def __init__(self, dfa: DFA, code: str, unclosed_comment_states: List[int]) -> None:
        Scanner.instance = self
        self._dfa = dfa
        self._code = code
        self._unclosed_comment_states = unclosed_comment_states
        self._token_start = 0
        self._lineno = 1
        self.symbol_table = OrderedDict({
            kw: i + 1 for i, kw in enumerate(KEYWORDS)
        })

    def has_next_token(self) -> bool:
        return self._token_start < len(self._code)

    def get_next_token(self) -> Token:
        """ Returns the next token type and its lexeme.

        Returns:
            Token: Line number, the next token type and its lexeme.
        """
        if not self.has_next_token():
            return Token(TokenType.EOF, '$', self._lineno)

        try:
            next_token_type, next_token_lexeme = self._next_token_lookahead()
        except ScannerError as e:
            self._token_start += len(e.lexeme)
            raise

        self._token_start += len(next_token_lexeme)
        self._add_to_symbol_table(next_token_type, next_token_lexeme)

        try:
            return Token(next_token_type, next_token_lexeme, self._lineno)
        finally:
            self._lineno += next_token_lexeme.count('\n')
            if next_token_type in [TokenType.WHITESPACE, TokenType.COMMENT]:
                return self.get_next_token()

    def _add_to_symbol_table(self, token_type: TokenType, lexeme: str) -> None:
        if token_type in [TokenType.ID, TokenType.KEYWORD]:
            if lexeme not in self.symbol_table:
                self.symbol_table[lexeme] = len(self.symbol_table) + 1

    def _next_token_lookahead(self) -> Tuple[TokenType, str]:
        current_state = self._dfa.start_state
        for i in range(self._token_start, len(self._code)):

            next_state = current_state.transition(self._code[i])

            if isinstance(current_state, ErrorState):
                if not isinstance(next_state, ErrorState):
                    self._error(current_state.message, end=i)

            if isinstance(current_state, FinalState):
                if not isinstance(next_state, (FinalState, ErrorState)):
                    return self._get_token(current_state, i)

            if next_state is None:
                self._error('Invalid input', end=i)

            current_state = next_state

        try:
            if isinstance(current_state, ErrorState):
                self._error(current_state.message)
            
            if isinstance(current_state, FinalState):
                return self._get_token(current_state)

            if current_state.id in self._unclosed_comment_states:
                lexeme = self._code[self._token_start:]
                if len(lexeme) > 7:
                    lexeme = lexeme[:7] + '...'
                self._error('Unclosed comment', lexeme=lexeme)

            self._error('Invalid input')
        finally:
            self._token_start = len(self._code)

    def _error(self, message: str, lexeme: str = None, end: int = None) -> None:
        raise ScannerError(message, self._lineno, lexeme or self._code[self._token_start:end])

    def _get_token(self, state: State, end: int = None) -> Tuple[TokenType, str]:
        lexeme = self._code[self._token_start:end]
        token_type = state.resolve_token_type(lexeme)
        return token_type, lexeme
