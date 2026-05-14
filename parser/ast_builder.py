"""Reduction actions for building AST nodes."""

from __future__ import annotations


def reduce_ast(lhs: str, rhs: list[str], children: list[dict]) -> dict:
    signature = (lhs, tuple(rhs))

    # Program / global items
    if signature == ("Program", ("GlobalItems",)):
        return {"node": "Program", "globals": children[0]["items"]}
    if signature == ("GlobalItems", ("GlobalItem", "GlobalItems")):
        return {"node": "GlobalItems", "items": [children[0]] + children[1]["items"]}
    if signature == ("GlobalItems", ()):
        return {"node": "GlobalItems", "items": []}

    if signature == ("GlobalItem", ("UsingDecl", "SEMI")):
        return children[0]
    if signature == ("GlobalItem", ("FuncDef",)):
        return children[0]
    if signature == ("GlobalItem", ("DeclStmt", "SEMI")):
        return {"node": "GlobalDecl", "decl": children[0]}

    if signature == ("UsingDecl", ("USING", "NAMESPACE", "ID")):
        return {"node": "UsingNamespace", "name": children[2]["lexeme"]}

    # Functions / parameters
    if signature == ("FuncDef", ("TYPE", "ID", "LPAREN", "ParamsOpt", "RPAREN", "Block")):
        return {
            "node": "Function",
            "return_type": children[0]["lexeme"],
            "name": children[1]["lexeme"],
            "params": children[3]["items"],
            "body": children[5],
        }
    if signature == ("ParamsOpt", ("Params",)):
        return children[0]
    if signature == ("ParamsOpt", ()):
        return {"node": "Params", "items": []}
    if signature == ("Params", ("Param", "ParamsTail")):
        return {"node": "Params", "items": [children[0]] + children[1]["items"]}
    if signature == ("ParamsTail", ("COMMA", "Param", "ParamsTail")):
        return {"node": "ParamsTail", "items": [children[1]] + children[2]["items"]}
    if signature == ("ParamsTail", ()):
        return {"node": "ParamsTail", "items": []}
    if signature == ("Param", ("TYPE", "ID")):
        return {"node": "Param", "var_type": children[0]["lexeme"], "name": children[1]["lexeme"]}

    # Blocks / statements
    if signature == ("Block", ("LBRACE", "Stmts", "RBRACE")):
        return {"node": "Block", "stmts": children[1]["items"]}

    if signature == ("Stmts", ("Stmt", "Stmts")):
        return {"node": "Stmts", "items": [children[0]] + children[1]["items"]}
    if signature == ("Stmts", ()):
        return {"node": "Stmts", "items": []}

    if signature == ("Stmt", ("MatchedStmt",)):
        return children[0]
    if signature == ("Stmt", ("UnmatchedStmt",)):
        return children[0]

    # Matched statements (includes if-with-else)
    if signature == ("MatchedStmt", ("DeclStmt", "SEMI")):
        return {"node": "DeclStmt", "decl": children[0]}
    if signature == ("MatchedStmt", ("ExprStmt", "SEMI")):
        return {"node": "ExprStmt", "expr": children[0]["expr"]}
    if signature == ("MatchedStmt", ("IOStmt", "SEMI")):
        return children[0]
    if signature == ("MatchedStmt", ("ForStmt",)):
        return children[0]
    if signature == ("MatchedStmt", ("ReturnStmt", "SEMI")):
        return children[0]
    if signature == ("MatchedStmt", ("Block",)):
        return children[0]
    if signature == ("MatchedStmt", ("IF", "LPAREN", "Expr", "RPAREN", "MatchedStmt", "ELSE", "MatchedStmt")):
        return {"node": "If", "cond": children[2], "then": children[4], "else": children[6]}

    # Unmatched statements (if-without-else, or else that still needs binding)
    if signature == ("UnmatchedStmt", ("IF", "LPAREN", "Expr", "RPAREN", "Stmt")):
        return {"node": "If", "cond": children[2], "then": children[4], "else": None}
    if signature == ("UnmatchedStmt", ("IF", "LPAREN", "Expr", "RPAREN", "MatchedStmt", "ELSE", "UnmatchedStmt")):
        return {"node": "If", "cond": children[2], "then": children[4], "else": children[6]}

    if signature == ("ReturnStmt", ("RETURN", "ExprOpt")):
        return {"node": "Return", "expr": children[1].get("expr")}
    if signature == ("ExprOpt", ("Expr",)):
        return {"node": "ExprOpt", "expr": children[0]}
    if signature == ("ExprOpt", ()):
        return {"node": "ExprOpt", "expr": None}

    if signature == ("ForStmt", ("FOR", "LPAREN", "ForInitOpt", "SEMI", "ExprOpt", "SEMI", "ExprOpt", "RPAREN", "Stmt")):
        return {
            "node": "For",
            "init": children[2].get("init"),
            "cond": children[4].get("expr"),
            "update": children[6].get("expr"),
            "body": children[8],
        }
    if signature == ("ForInitOpt", ("DeclStmt",)):
        return {"node": "ForInitOpt", "init": {"node": "DeclStmt", "decl": children[0]}}
    if signature == ("ForInitOpt", ("ExprOpt",)):
        return {"node": "ForInitOpt", "init": children[0].get("expr")}

    # Declarations
    if signature == ("DeclStmt", ("TYPE", "Declarators")):
        return {"node": "Decl", "var_type": children[0]["lexeme"], "declarators": children[1]["items"]}
    if signature == ("Declarators", ("Declarator", "DeclaratorsTail")):
        return {"node": "Declarators", "items": [children[0]] + children[1]["items"]}
    if signature == ("DeclaratorsTail", ("COMMA", "Declarator", "DeclaratorsTail")):
        return {"node": "DeclaratorsTail", "items": [children[1]] + children[2]["items"]}
    if signature == ("DeclaratorsTail", ()):
        return {"node": "DeclaratorsTail", "items": []}

    if signature == ("Declarator", ("ID", "ArrayOpt", "InitOpt")):
        return {
            "node": "Declarator",
            "name": children[0]["lexeme"],
            "array": children[1].get("array"),
            "init": children[2].get("init"),
        }
    if signature == ("ArrayOpt", ("LBRACKET", "ArraySizeOpt", "RBRACKET")):
        return {"node": "ArrayOpt", "array": {"size": children[1].get("size")}}
    if signature == ("ArrayOpt", ()):
        return {"node": "ArrayOpt", "array": None}
    if signature == ("ArraySizeOpt", ("NUM",)):
        lex = children[0]["lexeme"]
        return {"node": "ArraySizeOpt", "size": int(float(lex))}
    if signature == ("ArraySizeOpt", ()):
        return {"node": "ArraySizeOpt", "size": None}

    if signature == ("InitOpt", ("ASSIGN", "Initializer")):
        return {"node": "InitOpt", "init": children[1]}
    if signature == ("InitOpt", ()):
        return {"node": "InitOpt", "init": None}
    if signature == ("Initializer", ("Expr",)):
        return children[0]
    if signature == ("Initializer", ("LBRACE", "InitListOpt", "RBRACE")):
        return {"node": "InitList", "items": children[1]["items"]}
    if signature == ("InitListOpt", ("InitList",)):
        return children[0]
    if signature == ("InitListOpt", ()):
        return {"node": "InitList", "items": []}
    if signature == ("InitList", ("Expr", "InitListTail")):
        return {"node": "InitList", "items": [children[0]] + children[1]["items"]}
    if signature == ("InitListTail", ("COMMA", "Expr", "InitListTail")):
        return {"node": "InitListTail", "items": [children[1]] + children[2]["items"]}
    if signature == ("InitListTail", ()):
        return {"node": "InitListTail", "items": []}

    # Expression statement
    if signature == ("ExprStmt", ("Expr",)):
        return {"node": "ExprStmt", "expr": children[0]}

    # I/O statements (cout/cin)
    if signature == ("IOStmt", ("COUT", "CoutTail")):
        return {"node": "Cout", "items": children[1]["items"]}
    if signature == ("IOStmt", ("CIN", "CinTail")):
        return {"node": "Cin", "targets": children[1]["items"]}
    # std::cout and std::cin (children: ID=std, SCOPE, COUT/CIN, CoutTail/CinTail)
    if signature == ("IOStmt", ("ID", "SCOPE", "COUT", "CoutTail")):
        return {"node": "Cout", "items": children[3]["items"], "qualified": True}
    if signature == ("IOStmt", ("ID", "SCOPE", "CIN", "CinTail")):
        return {"node": "Cin", "targets": children[3]["items"], "qualified": True}
    if signature == ("CoutTail", ("LSHIFT", "CoutItem", "CoutTail")):
        return {"node": "CoutTail", "items": [children[1]] + children[2]["items"]}
    if signature == ("CoutTail", ()):
        return {"node": "CoutTail", "items": []}
    if signature == ("CoutItem", ("Expr",)):
        return children[0]
    if signature == ("CoutItem", ("ENDL",)):
        return {"node": "Endl"}
    if signature == ("CinTail", ("RSHIFT", "CinTarget", "CinTail")):
        return {"node": "CinTail", "items": [children[1]] + children[2]["items"]}
    if signature == ("CinTail", ()):
        return {"node": "CinTail", "items": []}
    if signature == ("CinTarget", ("ID", "LBRACKET", "Expr", "RBRACKET")):
        return {"node": "CinTargetIndex", "name": children[0]["lexeme"], "index": children[2]}
    if signature == ("CinTarget", ("ID",)):
        return {"node": "CinTargetVar", "name": children[0]["lexeme"]}

    # Expressions
    if signature == ("Expr", ("AssignExpr",)):
        return children[0]
    if signature == ("AssignExpr", ("OrExpr", "AssignTail")):
        if children[1].get("expr") is None:
            return children[0]
        return {"node": "AssignExpr", "target": children[0], "value": children[1]["expr"]}
    if signature == ("AssignTail", ("ASSIGN", "AssignExpr")):
        return {"node": "AssignTail", "expr": children[1]}
    if signature == ("AssignTail", ()):
        return {"node": "AssignTail", "expr": None}

    def _fold_left(first_expr: dict, tail_items: list[tuple[str, dict]]) -> dict:
        expr = first_expr
        for op, rhs_expr in tail_items:
            expr = {"node": "BinOp", "op": op, "left": expr, "right": rhs_expr}
        return expr

    if signature == ("OrExpr", ("AndExpr", "OrTail")):
        return _fold_left(children[0], children[1]["items"])
    if signature == ("OrTail", ("OR", "AndExpr", "OrTail")):
        return {"node": "OrTail", "items": [("||", children[1])] + children[2]["items"]}
    if signature == ("OrTail", ()):
        return {"node": "OrTail", "items": []}

    if signature == ("AndExpr", ("EqualityExpr", "AndTail")):
        return _fold_left(children[0], children[1]["items"])
    if signature == ("AndTail", ("AND", "EqualityExpr", "AndTail")):
        return {"node": "AndTail", "items": [("&&", children[1])] + children[2]["items"]}
    if signature == ("AndTail", ()):
        return {"node": "AndTail", "items": []}

    if signature == ("EqualityExpr", ("RelExpr", "EqTail")):
        return _fold_left(children[0], children[1]["items"])
    if signature == ("EqTail", ("EQ", "RelExpr", "EqTail")):
        return {"node": "EqTail", "items": [("==", children[1])] + children[2]["items"]}
    if signature == ("EqTail", ("NE", "RelExpr", "EqTail")):
        return {"node": "EqTail", "items": [("!=", children[1])] + children[2]["items"]}
    if signature == ("EqTail", ()):
        return {"node": "EqTail", "items": []}

    if signature == ("RelExpr", ("AddExpr", "RelTail")):
        return _fold_left(children[0], children[1]["items"])
    if signature == ("RelTail", ("LT", "AddExpr", "RelTail")):
        return {"node": "RelTail", "items": [("<", children[1])] + children[2]["items"]}
    if signature == ("RelTail", ("GT", "AddExpr", "RelTail")):
        return {"node": "RelTail", "items": [(">", children[1])] + children[2]["items"]}
    if signature == ("RelTail", ("LE", "AddExpr", "RelTail")):
        return {"node": "RelTail", "items": [("<=", children[1])] + children[2]["items"]}
    if signature == ("RelTail", ("GE", "AddExpr", "RelTail")):
        return {"node": "RelTail", "items": [(">=", children[1])] + children[2]["items"]}
    if signature == ("RelTail", ()):
        return {"node": "RelTail", "items": []}

    if signature == ("AddExpr", ("MulExpr", "AddTail")):
        return _fold_left(children[0], children[1]["items"])
    if signature == ("AddTail", ("PLUS", "MulExpr", "AddTail")):
        return {"node": "AddTail", "items": [("+", children[1])] + children[2]["items"]}
    if signature == ("AddTail", ("MINUS", "MulExpr", "AddTail")):
        return {"node": "AddTail", "items": [("-", children[1])] + children[2]["items"]}
    if signature == ("AddTail", ()):
        return {"node": "AddTail", "items": []}

    if signature == ("MulExpr", ("UnaryExpr", "MulTail")):
        return _fold_left(children[0], children[1]["items"])
    if signature == ("MulTail", ("MUL", "UnaryExpr", "MulTail")):
        return {"node": "MulTail", "items": [("*", children[1])] + children[2]["items"]}
    if signature == ("MulTail", ("DIV", "UnaryExpr", "MulTail")):
        return {"node": "MulTail", "items": [("/", children[1])] + children[2]["items"]}
    if signature == ("MulTail", ("MOD", "UnaryExpr", "MulTail")):
        return {"node": "MulTail", "items": [("%", children[1])] + children[2]["items"]}
    if signature == ("MulTail", ()):
        return {"node": "MulTail", "items": []}

    # Prefix ++ / --
    if signature == ("UnaryExpr", ("INC", "UnaryExpr")):
        return {"node": "IncDec", "op": "++", "kind": "pre", "target": children[1]}
    if signature == ("UnaryExpr", ("DEC", "UnaryExpr")):
        return {"node": "IncDec", "op": "--", "kind": "pre", "target": children[1]}

    if signature == ("UnaryExpr", ("NOT", "UnaryExpr")):
        return {"node": "UnaryOp", "op": "!", "expr": children[1]}
    if signature == ("UnaryExpr", ("MINUS", "UnaryExpr")):
        return {"node": "UnaryOp", "op": "-", "expr": children[1]}
    if signature == ("UnaryExpr", ("PostfixExpr",)):
        return children[0]

    # Postfix indexing + optional postfix ++ / --
    if signature == ("PostfixExpr", ("Primary", "PostfixTail", "PostfixIncDecOpt")):
        expr = children[0]
        for idx_expr in children[1]["items"]:
            expr = {"node": "Index", "base": expr, "index": idx_expr}
        incdec = children[2].get("incdec")
        if incdec is None:
            return expr
        return {"node": "IncDec", "op": incdec, "kind": "post", "target": expr}
    if signature == ("PostfixTail", ("LBRACKET", "Expr", "RBRACKET", "PostfixTail")):
        return {"node": "PostfixTail", "items": [children[1]] + children[3]["items"]}
    if signature == ("PostfixTail", ()):
        return {"node": "PostfixTail", "items": []}
    if signature == ("PostfixIncDecOpt", ("INC",)):
        return {"node": "PostfixIncDecOpt", "incdec": "++"}
    if signature == ("PostfixIncDecOpt", ("DEC",)):
        return {"node": "PostfixIncDecOpt", "incdec": "--"}
    if signature == ("PostfixIncDecOpt", ()):
        return {"node": "PostfixIncDecOpt", "incdec": None}

    if signature == ("Primary", ("LPAREN", "Expr", "RPAREN")):
        return children[1]
    if signature == ("Primary", ("ID",)):
        return {"node": "Identifier", "name": children[0]["lexeme"]}
    if signature == ("Primary", ("NUM",)):
        lex = children[0]["lexeme"]
        return {"node": "Number", "value": float(lex) if "." in lex else int(lex)}
    if signature == ("Primary", ("STRING_LIT",)):
        return {"node": "String", "value": children[0]["lexeme"]}
    if signature == ("Primary", ("CHAR_LIT",)):
        return {"node": "Char", "value": children[0]["lexeme"]}
    if signature == ("Primary", ("BOOL_LIT",)):
        return {"node": "Bool", "value": True if children[0]["lexeme"] == "true" else False}

    return {"node": lhs, "children": children}
