# Context-Free Grammar (CFG)

This file documents the full context-free grammar used by the LR(1) parser.
The grammar is defined in `grammar.txt` and loaded at runtime.

---

## Notation

| Symbol      | Meaning                                    |
|-------------|--------------------------------------------|
| `->`        | Production rule (derives)                  |
| `|`         | Alternative production                     |
| `eps`       | The empty string (epsilon / ε)             |
| `UPPER`     | Terminal token (produced by the lexer)     |
| `CamelCase` | Non-terminal symbol                        |

---

## Start Symbol

```
Program
```

---

## Grammar Rules

### Top-level structure

```
Program     -> GlobalItems

GlobalItems -> GlobalItem GlobalItems
             | eps

GlobalItem  -> UsingDecl SEMI
             | FuncDef
             | DeclStmt SEMI
```

### Using directive

```
UsingDecl -> USING NAMESPACE ID
```

### Function definition

```
FuncDef    -> TYPE ID LPAREN ParamsOpt RPAREN Block

ParamsOpt  -> Params
            | eps

Params     -> Param ParamsTail

ParamsTail -> COMMA Param ParamsTail
            | eps

Param      -> TYPE ID
```

### Block and statements

```
Block -> LBRACE Stmts RBRACE

Stmts -> Stmt Stmts
       | eps

Stmt  -> MatchedStmt
       | UnmatchedStmt
```

### Matched vs unmatched (dangling-else resolution)

The grammar encodes the standard rule that `else` always binds to the
nearest `if`.  A `MatchedStmt` is an if whose every branch is fully
closed; an `UnmatchedStmt` is one that still has an open else.

```
MatchedStmt -> DeclStmt SEMI
             | ExprStmt SEMI
             | IOStmt SEMI
             | ForStmt
             | ReturnStmt SEMI
             | Block
             | IF LPAREN Expr RPAREN MatchedStmt ELSE MatchedStmt

UnmatchedStmt -> IF LPAREN Expr RPAREN Stmt
               | IF LPAREN Expr RPAREN MatchedStmt ELSE UnmatchedStmt
```

### I/O statements

```
IOStmt   -> COUT CoutTail
           | CIN  CinTail

CoutTail -> LSHIFT CoutItem CoutTail
           | eps

CoutItem -> Expr
           | ENDL

CinTail  -> RSHIFT ID CinTail
           | eps
```

### Return

```
ReturnStmt -> RETURN ExprOpt

ExprOpt -> Expr
         | eps
```

### For loop

```
ForStmt    -> FOR LPAREN ForInitOpt SEMI ExprOpt SEMI ExprOpt RPAREN Stmt

ForInitOpt -> DeclStmt
            | ExprOpt
```

### Declarations

```
DeclStmt        -> TYPE Declarators

Declarators     -> Declarator DeclaratorsTail

DeclaratorsTail -> COMMA Declarator DeclaratorsTail
                 | eps

Declarator      -> ID ArrayOpt InitOpt

ArrayOpt        -> LBRACKET ArraySizeOpt RBRACKET
                 | eps

ArraySizeOpt    -> NUM
                 | eps

InitOpt         -> ASSIGN Initializer
                 | eps

Initializer     -> Expr
                 | LBRACE InitListOpt RBRACE

InitListOpt     -> InitList
                 | eps

InitList        -> Expr InitListTail

InitListTail    -> COMMA Expr InitListTail
                 | eps
```

### Expression (precedence, lowest to highest)

```
ExprStmt   -> Expr

Expr       -> AssignExpr

AssignExpr -> OrExpr AssignTail

AssignTail -> ASSIGN AssignExpr
            | eps

OrExpr  -> AndExpr OrTail
OrTail  -> OR AndExpr OrTail
          | eps

AndExpr -> EqualityExpr AndTail
AndTail -> AND EqualityExpr AndTail
          | eps

EqualityExpr -> RelExpr EqTail
EqTail       -> EQ RelExpr EqTail
              | NE RelExpr EqTail
              | eps

RelExpr  -> AddExpr RelTail
RelTail  -> LT  AddExpr RelTail
           | GT  AddExpr RelTail
           | LE  AddExpr RelTail
           | GE  AddExpr RelTail
           | eps

AddExpr  -> MulExpr AddTail
AddTail  -> PLUS  MulExpr AddTail
           | MINUS MulExpr AddTail
           | eps

MulExpr  -> UnaryExpr MulTail
MulTail  -> MUL UnaryExpr MulTail
           | DIV UnaryExpr MulTail
           | MOD UnaryExpr MulTail
           | eps

UnaryExpr -> INC UnaryExpr
           | DEC UnaryExpr
           | NOT UnaryExpr
           | MINUS UnaryExpr
           | PostfixExpr

PostfixExpr      -> Primary PostfixTail PostfixIncDecOpt
PostfixTail      -> LBRACKET Expr RBRACKET PostfixTail
                  | eps
PostfixIncDecOpt -> INC
                  | DEC
                  | eps

Primary -> LPAREN Expr RPAREN
         | ID
         | NUM
         | STRING_LIT
         | CHAR_LIT
         | BOOL_LIT
```

---

## Terminal Tokens (produced by the Lexer)

| Token        | Lexeme examples           |
|--------------|---------------------------|
| `TYPE`       | `int`, `float`, `bool`, … |
| `ID`         | any identifier            |
| `NUM`        | `42`, `3.14`              |
| `STRING_LIT` | `"hello"`                 |
| `CHAR_LIT`   | `'a'`                     |
| `BOOL_LIT`   | `true`, `false`           |
| `FOR`        | `for`                     |
| `IF`         | `if`                      |
| `ELSE`       | `else`                    |
| `RETURN`     | `return`                  |
| `USING`      | `using`                   |
| `NAMESPACE`  | `namespace`               |
| `CIN`        | `cin`                     |
| `COUT`       | `cout`                    |
| `ENDL`       | `endl`                    |
| `SEMI`       | `;`                       |
| `COMMA`      | `,`                       |
| `ASSIGN`     | `=`                       |
| `PLUS`       | `+`                       |
| `MINUS`      | `-`                       |
| `MUL`        | `*`                       |
| `DIV`        | `/`                       |
| `MOD`        | `%`                       |
| `INC`        | `++`                      |
| `DEC`        | `--`                      |
| `EQ`         | `==`                      |
| `NE`         | `!=`                      |
| `LT`         | `<`                       |
| `GT`         | `>`                       |
| `LE`         | `<=`                      |
| `GE`         | `>=`                      |
| `AND`        | `&&`                      |
| `OR`         | `\|\|`                    |
| `NOT`        | `!`                       |
| `LSHIFT`     | `<<`                      |
| `RSHIFT`     | `>>`                      |
| `LPAREN`     | `(`                       |
| `RPAREN`     | `)`                       |
| `LBRACE`     | `{`                       |
| `RBRACE`     | `}`                       |
| `LBRACKET`   | `[`                       |
| `RBRACKET`   | `]`                       |
| `EOF`        | end of input (`$`)        |

---

## Parser type

The parser is **canonical LR(1)**.  Shift/reduce conflicts that arise
from the dangling-else ambiguity are resolved by preferring shift
(standard C++ rule: else binds to the nearest if).
