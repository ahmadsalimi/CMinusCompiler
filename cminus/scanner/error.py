class ScannerError(Exception):

    def __init__(self, message: str, lineno: int, lexeme: int) -> None:
        super().__init__(message)
        self.message = message
        self.lineno = lineno
        self.lexeme = lexeme
