from __future__ import annotations

from lexer.rules import DOUBLE_CHAR_TOKENS, KEYWORDS, SINGLE_CHAR_TOKENS
from lexer.token import Token
from utils.error import CompilerError


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._is_at_end():
            ch = self._peek()
            if ch in (" ", "\t", "\r"):
                self._advance()
                continue
            if ch == "\n":
                self._advance_line()
                continue
            if ch == "/" and self._peek_next() == "/":
                self._skip_line_comment()
                continue
            if ch == "/" and self._peek_next() == "*":
                self._skip_block_comment()
                continue
            if ch == '"':
                self._string_literal()
                continue
            if ch == "'":
                self._char_literal()
                continue
            if ch.isalpha() or ch == "_":
                self._identifier_or_keyword()
                continue
            if ch.isdigit():
                self._number()
                continue
            self._operator_or_punctuation()

        self.tokens.append(Token("EOF", "$", self.line, self.column))
        return self.tokens

    def _is_at_end(self) -> bool:
        return self.index >= len(self.source)

    def _peek(self) -> str:
        return self.source[self.index]

    def _peek_next(self) -> str:
        if self.index + 1 >= len(self.source):
            return "\0"
        return self.source[self.index + 1]

    def _advance(self) -> str:
        ch = self.source[self.index]
        self.index += 1
        self.column += 1
        return ch

    def _advance_line(self) -> None:
        self.index += 1
        self.line += 1
        self.column = 1

    def _skip_line_comment(self) -> None:
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self) -> None:
        self._advance()  # /
        self._advance()  # *
        while not self._is_at_end():
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                return
            if self._peek() == "\n":
                self._advance_line()
            else:
                self._advance()
        raise CompilerError("Unterminated block comment.")

    def _identifier_or_keyword(self) -> None:
        start = self.index
        line = self.line
        col = self.column
        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        lexeme = self.source[start : self.index]
        token_type = KEYWORDS.get(lexeme, "ID")
        self.tokens.append(Token(token_type, lexeme, line, col))

    def _number(self) -> None:
        start = self.index
        line = self.line
        col = self.column
        has_dot = False
        while not self._is_at_end():
            ch = self._peek()
            if ch == "." and not has_dot:
                has_dot = True
                self._advance()
            elif ch.isdigit():
                self._advance()
            else:
                break
        lexeme = self.source[start : self.index]
        self.tokens.append(Token("NUM", lexeme, line, col))

    def _string_literal(self) -> None:
        line = self.line
        col = self.column
        self._advance()  # opening "
        value_chars: list[str] = []
        while not self._is_at_end():
            ch = self._peek()
            if ch == '"':
                self._advance()
                lexeme = "".join(value_chars)
                self.tokens.append(Token("STRING_LIT", lexeme, line, col))
                return
            if ch == "\n":
                raise CompilerError(f"Unterminated string literal at line {line}, column {col}.")
            if ch == "\\":
                self._advance()
                if self._is_at_end():
                    break
                esc = self._advance()
                value_chars.append("\\" + esc)
            else:
                value_chars.append(self._advance())
        raise CompilerError(f"Unterminated string literal at line {line}, column {col}.")

    def _char_literal(self) -> None:
        line = self.line
        col = self.column
        self._advance()  # opening '
        if self._is_at_end() or self._peek() == "\n":
            raise CompilerError(f"Unterminated char literal at line {line}, column {col}.")
        ch = self._advance()
        if ch == "\\":
            if self._is_at_end():
                raise CompilerError(f"Unterminated char literal at line {line}, column {col}.")
            esc = self._advance()
            value = "\\" + esc
        else:
            value = ch
        if self._is_at_end() or self._peek() != "'":
            raise CompilerError(f"Unterminated char literal at line {line}, column {col}.")
        self._advance()  # closing '
        self.tokens.append(Token("CHAR_LIT", value, line, col))

    def _operator_or_punctuation(self) -> None:
        line = self.line
        col = self.column
        two = self.source[self.index : self.index + 2]
        if two in DOUBLE_CHAR_TOKENS:
            self._advance()
            self._advance()
            self.tokens.append(Token(DOUBLE_CHAR_TOKENS[two], two, line, col))
            return
        one = self._advance()
        if one in SINGLE_CHAR_TOKENS:
            self.tokens.append(Token(SINGLE_CHAR_TOKENS[one], one, line, col))
            return
        raise CompilerError(f"Unexpected character '{one}' at line {line}, column {col}.")
