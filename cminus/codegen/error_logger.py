class CodeGenErrorLogger:
    instance: 'CodeGenErrorLogger' = None

    def __init__(self, file_name: str):
        CodeGenErrorLogger.instance = self
        self.file_name = file_name
        self.log_file = None
        self.any_error = False

    def __enter__(self):
        self.log_file = open(self.file_name, 'w')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.any_error:
            self.log_file.write('The input program is semantically correct.\n')
        self.log_file.close()

    def log(self, lineno: int, message: str) -> None:
        formatted = f'#{lineno} : Semantic Error! {message}\n'
        self.log_file.write(formatted)
        self.any_error = True
