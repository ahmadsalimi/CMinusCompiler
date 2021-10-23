from typing import List, Tuple
from collections import OrderedDict

from .dfa import DFA, ErrorState, FinalState, TokenType
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

    def __init__(self, dfa: DFA, code: str, unclosed_comment_states: List[int]) -> None:
        self._dfa = dfa
        self._code = code
        self._unclosed_comment_states = unclosed_comment_states
        self._token_start = 0
        self._last_token: Tuple[TokenType, str] = None
        self._lineno = 1
        self.symbol_table = OrderedDict({
            kw: i + 1 for i, kw in enumerate(KEYWORDS)
        })

    def panic_mode(self, length: int):
        self._token_start += length
        current_position = self._token_start
        while current_position < len(self._code):
            try:
                self._next_token_lookahead()
                break
            except ScannerError:
                self._token_start += 1
                continue
        return self._code[current_position:self._token_start]

    def has_next_token(self) -> bool:
        return self._token_start < len(self._code)

    def get_next_token(self) -> Tuple[int, TokenType, str]:
        """ Returns the next token type and its lexeme.

        Returns:
            Tuple[int, TokenType, str]: Line number, the next token type and its lexeme.
        """
        try:
            next_token_type, next_token_lexeme = self._next_token_lookahead()
        except ScannerError as e:
            lexeme = e.lexeme + self.panic_mode(len(e.lexeme))
            raise ScannerError(e.message, e.lineno, lexeme)

        self._token_start += len(next_token_lexeme)
        self._last_token = next_token_type, next_token_lexeme

        current_lineno = self._lineno
        self._lineno += next_token_lexeme.count('\n')

        if next_token_type in [TokenType.ID, TokenType.KEYWORD]:
            if next_token_lexeme not in self.symbol_table:
                self.symbol_table[next_token_lexeme] = len(self.symbol_table) + 1

        return current_lineno, next_token_type, next_token_lexeme

    def _next_token_lookahead(self) -> Tuple[TokenType, str]:
        current_state = self._dfa.start_state
        for i in range(self._token_start, len(self._code)):
            if current_state is None:
                raise ScannerError('Invalid input', self._lineno, f'{self._code[self._token_start:i - 1]}')

            c = self._code[i]
            next_state = current_state.transition(c)

            if isinstance(current_state, ErrorState):
                if not isinstance(next_state, ErrorState):
                    raise ScannerError(current_state.message, self._lineno, f'{self._code[self._token_start:i]}')

            if isinstance(current_state, FinalState):
                if not isinstance(next_state, (FinalState, ErrorState)):
                    lexeme = self._code[self._token_start:i]
                    token_type = current_state.resolve_token_type(lexeme)
                    return token_type, lexeme

            current_state = next_state

        if isinstance(current_state, ErrorState):
            raise ScannerError(current_state.message, self._lineno, f'{self._code[self._token_start:]}')
        
        if isinstance(current_state, FinalState):
            lexeme = self._code[self._token_start:]
            token_type = current_state.resolve_token_type(lexeme)
            return token_type, lexeme

        current_token_start, self._token_start = self._token_start, len(self._code)

        if current_state.id in self._unclosed_comment_states:
            raise ScannerError('Unclosed comment', self._lineno, self._code[current_token_start:])

        raise ScannerError('Invalid input', self._lineno, f'{self._code[current_token_start:]}')
