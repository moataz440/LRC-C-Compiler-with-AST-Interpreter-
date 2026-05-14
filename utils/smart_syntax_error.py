from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmartSyntaxErrorDetail:
    unexpected_lexeme: str
    unexpected_type: str
    line: int
    column: int
    expected_types: list[str]
    hints: list[str]

    def format_message(self) -> str:
        expected_pretty = ", ".join(_pretty_token(t) for t in self.expected_types) if self.expected_types else "(none)"
        hints_block = ""
        if self.hints:
            hints_block = "\nPossible fixes:\n" + "\n".join(f"  - {h}" for h in self.hints)
        return (
            f"Syntax error at {self.unexpected_lexeme!r} ({self.unexpected_type}) "
            f"on line {self.line}, column {self.column}.\n"
            f"Expected: {expected_pretty}"
            f"{hints_block}"
        )


def build_smart_syntax_error(
    *,
    state: int,
    action_table: dict[tuple[int, str], tuple[str, object]],
    unexpected_type: str,
    unexpected_lexeme: str,
    line: int,
    column: int,
) -> SmartSyntaxErrorDetail:
    expected = sorted({sym for (st, sym) in action_table.keys() if st == state and sym != "EOF"})
    hints = _hints_from_expected(expected, unexpected_type, unexpected_lexeme)
    return SmartSyntaxErrorDetail(
        unexpected_lexeme=unexpected_lexeme,
        unexpected_type=unexpected_type,
        line=line,
        column=column,
        expected_types=expected,
        hints=hints,
    )


def _hints_from_expected(expected: list[str], unexpected_type: str, unexpected_lexeme: str) -> list[str]:
    hints: list[str] = []

    # High-signal missing punctuation.
    if "SEMI" in expected and unexpected_type in {"RBRACE", "EOF", "ELSE"}:
        hints.append("You may be missing a ';' before this token.")
    if "RBRACE" in expected and unexpected_type == "EOF":
        hints.append("You may be missing a closing brace '}' at the end of the file.")
    if "RPAREN" in expected and unexpected_type in {"LBRACE", "SEMI"}:
        hints.append("You may be missing a closing parenthesis ')'.")
    if "RBRACKET" in expected and unexpected_type in {"SEMI", "RPAREN"}:
        hints.append("You may be missing a closing bracket ']'.")

    # Dangling else / block-related hints.
    if unexpected_type == "ELSE" and "ELSE" not in expected:
        hints.append("This 'else' does not match a preceding 'if'. Check braces '{...}' around your if-statement.")

    # Generic hint if we can show a small set of likely tokens.
    if not hints and expected:
        top = ", ".join(_pretty_token(t) for t in expected[:8])
        if len(expected) > 8:
            top += ", …"
        hints.append(f"Continue with one of: {top}")

    # Token-specific quick fix (very common).
    if unexpected_lexeme == "}" and "SEMI" in expected:
        hints.append("If the previous statement is missing ';', add it before '}'.")

    return hints


def _pretty_token(token_type: str) -> str:
    pretty = {
        "SEMI": "';'",
        "COMMA": "','",
        "LPAREN": "'('",
        "RPAREN": "')'",
        "LBRACE": "'{'",
        "RBRACE": "'}'",
        "LBRACKET": "'['",
        "RBRACKET": "']'",
        "ASSIGN": "'='",
        "PLUS": "'+'",
        "MINUS": "'-'",
        "MUL": "'*'",
        "DIV": "'/'",
        "MOD": "'%'",
        "LT": "'<'",
        "GT": "'>'",
        "LE": "'<='",
        "GE": "'>='",
        "EQ": "'=='",
        "NE": "'!='",
        "AND": "'&&'",
        "OR": "'||'",
        "NOT": "'!'",
        "ID": "identifier",
        "NUM": "number",
        "TYPE": "type",
        "BOOL_LIT": "boolean literal",
        "STRING_LIT": "string literal",
        "CHAR_LIT": "char literal",
        "IF": "'if'",
        "ELSE": "'else'",
        "FOR": "'for'",
        "RETURN": "'return'",
        "USING": "'using'",
        "NAMESPACE": "'namespace'",
        "EOF": "end of file",
    }
    return pretty.get(token_type, token_type)

