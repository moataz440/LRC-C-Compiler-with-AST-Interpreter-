from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    token_type: str
    lexeme: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "type": self.token_type,
            "lexeme": self.lexeme,
            "line": self.line,
            "column": self.column,
        }
