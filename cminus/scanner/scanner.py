from typing import Tuple
from collections import OrderedDict

from .dfa import DFA, FinalState, TokenType
from .error import ScannerError


KEYWORDS = [
    'if',
    'else',
    'void',
    'int',
    'repeat',
    'break',
    'until',
    'return'
]


class Scanner:

    def __init__(self, dfa: DFA, code: str) -> None:
        self._dfa = dfa
        self._code = code
        self._token_start = 0
        self._last_token: Tuple[TokenType, str] = None
        self._lineno = 1
        self.symbol_table = OrderedDict({
            kw: i + 1 for i, kw in enumerate(KEYWORDS)
        })


    def get_next_token(self) -> Tuple[int, TokenType, str]:
        """ Returns the next token type and its lexeme.

        Returns:
            Tuple[int, TokenType, str]: Line number, the next token type and its lexeme.
        """
        next_token_type, next_token_lexeme = self._next_token_lookahead()

        self._token_start += len(next_token_lexeme)
        self._last_token = next_token_type, next_token_lexeme

        current_lineno = self._lineno

        if next_token_lexeme.count('\n'):
            self._lineno += 1

        if next_token_type is TokenType.NUMBER:
            la_token_type, la_token_lexeme = self._next_token_lookahead()
            if la_token_type in [TokenType.IDENTIFIER, TokenType.KEYWORD]:
                raise ScannerError('Invalid number', self._lineno, f'{next_token_lexeme}{la_token_lexeme}')

        if next_token_type in [TokenType.IDENTIFIER, TokenType.KEYWORD]:
            if next_token_lexeme not in self.symbol_table:
                self.symbol_table[next_token_lexeme] = len(self.symbol_table) + 1

        return current_lineno, next_token_type, next_token_lexeme

    def _next_token_lookahead(self) -> Tuple[TokenType, str]:
        current_state = self._dfa.start_state

        for i in range(self._token_start, len(self._code)):
            if current_state is None:
                raise ScannerError('Invalid token', self._lineno, f'{self._code[self._token_start:i]}')

            c = self._code[i]
            next_state = current_state.transition(c)

            if isinstance(current_state, FinalState):
                if not isinstance(next_state, FinalState):
                    lexeme = self._code[self._token_start:i]
                    token_type = current_state.resolve_token_type(lexeme)
                    return token_type, lexeme

            current_state = next_state
