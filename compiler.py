from typing import Callable
from pprint import pprint

from cminus.scanner.dfa import DFA, State, FinalState, Transition, TokenType
from cminus.scanner.error import ScannerError
from cminus.scanner.scanner import Scanner, KEYWORDS


def create_cminus_dfa() -> DFA:
    dfa = DFA(State(1))
    

    def default_resolver(token_type: TokenType) -> Callable[[str], TokenType]:
        return lambda _: token_type

    finals = {
        2: default_resolver(TokenType.NUMBER),
        3: lambda token: TokenType.KEYWORD if token in KEYWORDS else TokenType.IDENTIFIER,
        4: default_resolver(TokenType.SYMBOL),
        5: default_resolver(TokenType.SYMBOL),
        8: default_resolver(TokenType.COMMENT),
        11: default_resolver(TokenType.WHITESPACE),
    }
    for i in range(2, 12):
        if i in finals:
            dfa.add_state(FinalState(i, finals[i]))
        else:
            dfa.add_state(State(i))

    dfa.add_transition(1, Transition(dfa.states[2], r'\d'))
    dfa.add_transition(2, Transition(dfa.states[2], r'\d'))

    dfa.add_transition(1, Transition(dfa.states[3], r'[a-zA-Z]'))
    dfa.add_transition(3, Transition(dfa.states[3], r'[a-zA-Z0-9]'))

    dfa.add_transition(1, Transition(dfa.states[4], r'[;:,\[\]\(\)\{\}\+\-\*<]'))
    dfa.add_transition(1, Transition(dfa.states[5], r'='))
    dfa.add_transition(5, Transition(dfa.states[4], r'='))

    dfa.add_transition(1, Transition(dfa.states[6], r'/'))
    dfa.add_transition(6, Transition(dfa.states[7], r'/'))
    dfa.add_transition(7, Transition(dfa.states[7], r'[^\n]'))
    dfa.add_transition(7, Transition(dfa.states[8], r'\n'))
    dfa.add_transition(6, Transition(dfa.states[9], r'\*'))
    dfa.add_transition(9, Transition(dfa.states[9], r'[^\*]'))
    dfa.add_transition(9, Transition(dfa.states[10], r'\*'))
    dfa.add_transition(10, Transition(dfa.states[9], r'[^\*/]'))
    dfa.add_transition(10, Transition(dfa.states[10], r'\*'))
    dfa.add_transition(10, Transition(dfa.states[8], r'/'))

    dfa.add_transition(1, Transition(dfa.states[11], r'\s'))

    return dfa


INPUT_FILE = 'input.txt'


if __name__ == '__main__':
    with open(INPUT_FILE, 'r') as f:
        code = f.read()

    dfa = create_cminus_dfa()
    scanner = Scanner(dfa, code)

    # import pdb; pdb.set_trace()

    try:
        while True:
            lineno, token_type, lexeme = scanner.get_next_token()
            if token_type not in [TokenType.WHITESPACE, TokenType.COMMENT]:
                print(f'{lineno:>3}: {token_type.name:<10} {lexeme}')
    except ScannerError as e:
        print(e.lineno, e.message, e.lexeme)
    finally:
        pprint(scanner.symbol_table)
