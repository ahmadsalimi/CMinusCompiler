import os
from typing import Callable, Dict, List, Tuple

from cminus.scanner.dfa import DFA, ErrorState, State, FinalState, Transition, TokenType
from cminus.scanner.error import ScannerError
from cminus.scanner.scanner import Scanner, KEYWORDS


def create_cminus_dfa() -> DFA:
    dfa = DFA(State(1))
    
    def default_resolver(token_type: TokenType) -> Callable[[str], TokenType]:
        return lambda _: token_type

    finals = {
        2: default_resolver(TokenType.NUM),
        3: lambda token: TokenType.KEYWORD if token in KEYWORDS else TokenType.ID,
        4: default_resolver(TokenType.SYMBOL),
        5: default_resolver(TokenType.SYMBOL),
        8: default_resolver(TokenType.COMMENT),
        11: default_resolver(TokenType.WHITESPACE),
        13: default_resolver(TokenType.SYMBOL),
    }
    error_states = {
        12: 'Invalid number',
        14: 'Unmatched comment',
        15: 'Invalid input',
    }
    for i in range(2, 16):
        if i in finals:
            dfa.add_state(FinalState(i, finals[i]))
        elif i in error_states:
            dfa.add_state(ErrorState(i, error_states[i]))
        else:
            dfa.add_state(State(i))

    ILLEGAL_CHARS = r'[^a-zA-Z0-9;:,\[\]\(\)\{\}\+\-<=\*/\s]'

    dfa.add_transition(1, Transition(dfa.states[2], r'\d'))
    dfa.add_transition(2, Transition(dfa.states[2], r'\d'))
    dfa.add_transition(2, Transition(dfa.states[12], r'([a-zA-Z]|' + ILLEGAL_CHARS + r')'))

    dfa.add_transition(1, Transition(dfa.states[3], r'[a-zA-Z]'))
    dfa.add_transition(3, Transition(dfa.states[3], r'[a-zA-Z0-9]'))
    dfa.add_transition(3, Transition(dfa.states[15], ILLEGAL_CHARS))

    dfa.add_transition(1, Transition(dfa.states[4], r'[;:,\[\]\(\)\{\}\+\-<]'))
    dfa.add_transition(1, Transition(dfa.states[5], r'='))
    dfa.add_transition(5, Transition(dfa.states[4], r'='))
    dfa.add_transition(1, Transition(dfa.states[13], r'\*'))
    dfa.add_transition(13, Transition(dfa.states[14], r'/'))
    dfa.add_transition(13, Transition(dfa.states[15], ILLEGAL_CHARS))
    dfa.add_transition(5, Transition(dfa.states[15], ILLEGAL_CHARS))

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

    dfa.add_transition(1, Transition(dfa.states[15], ILLEGAL_CHARS))

    return dfa


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Cminus Scanner')
    parser.add_argument('-i', '--input', default='input.txt', help='Input file')
    parser.add_argument('-o', '--output-directory', default='', help='Output directory')

    args = parser.parse_args()

    with open(args.input, 'r') as f:
        code = f.read()

    dfa = create_cminus_dfa()
    scanner = Scanner(dfa, code, [9, 10])

    current_line = None
    current_tokens: Dict[int, List[Tuple[TokenType, str]]] = {}
    errors: Dict[int, List[ScannerError]] = {}
    while scanner.has_next_token():
        try:
            lineno, token_type, lexeme = scanner.get_next_token()
            if token_type not in [TokenType.WHITESPACE, TokenType.COMMENT]:
                if lineno not in current_tokens:
                    current_tokens[lineno] = []
                current_tokens[lineno].append((token_type, lexeme))
        except ScannerError as e:
            if e.lineno not in errors:
                errors[e.lineno] = []
            errors[e.lineno].append(e)
    
    if args.output_directory != '':
        os.makedirs(args.output_directory, exist_ok=True)

    with open(os.path.join(args.output_directory, 'tokens.txt'), 'w') as f:
        for lineno, tokens in current_tokens.items():
            print(f'{lineno}.\t', file=f, end='')
            print(' '.join([
                f'({token_type.name}, {lexeme})'
                for token_type, lexeme in tokens
            ]), end=' \n', file=f, flush=True)

    with open(os.path.join(args.output_directory, 'lexical_errors.txt'), 'w') as f:
        if len(errors) == 0:
            print('There is no lexical error.', file=f, end='')
        for lineno, es in errors.items():
            print(f'{lineno}.\t', end='',
                  file=f, flush=True)
            print(' '.join([
                f'({e.lexeme}, {e.message})'
                for e in es
            ]), end=' \n', file=f, flush=True)

    with open(os.path.join(args.output_directory, 'symbol_table.txt'), 'w') as f:
        for lexeme, idx in scanner.symbol_table.items():
            print(f'{idx}.\t{lexeme}',
                  file=f, flush=True)
