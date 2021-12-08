from enum import Enum

from cminus.scanner.dfa import TokenType

from ..scanner.scanner import Token


class _ErrorType(Enum):
    IllegalToken = 'illegal'
    MissingToken = 'missing'
    UnexpectedEOF = 'Unexpected EOF'


class ParserErrorLogger:
    instance: 'ParserErrorLogger' = None

    def __init__(self, file_name: str):
        ParserErrorLogger.instance = self
        self.file_name = file_name
        self.log_file = open(file_name, 'w')

    def __log(self, lineno: int, errortype: _ErrorType, token: str = None) -> None:
        formatted = f'#{lineno} : syntax error, {errortype.value}'
        formatted += f' {token}\n' if token else '\n'
        self.log_file.write(formatted)

    def missing_token(self, lineno: int, lexeme: str):
        self.__log(lineno, _ErrorType.MissingToken, lexeme)

    def illegal_token(self, token: Token):
        lexeme = token.lexeme \
            if token.type not in [TokenType.ID, TokenType.NUM] \
            else token.type.name
        self.__log(token.lineno, _ErrorType.IllegalToken, lexeme)

    def unexpected_eof(self, lineno: int):
        self.__log(lineno, _ErrorType.UnexpectedEOF)
