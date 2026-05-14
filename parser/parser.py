from __future__ import annotations

from parser.ast_builder import reduce_ast
from parser.stack import Stack
from utils.error import CompilerError
from utils.smart_syntax_error import build_smart_syntax_error


class LRParser:
    """
    Canonical LR(1) parser.

    Accepts the action/goto tables produced by build_lr1_table() and drives
    the classic shift-reduce algorithm over a flat token list.  Three parallel
    stacks are maintained:

      state_stack  -- parser states (integers)
      ast_stack    -- partially-built AST nodes / token dicts
      parse_stack  -- concrete parse-tree nodes (for visualization)

    The parse result contains the final AST, the concrete parse tree, and a
    full step-by-step LR trace for the GUI.
    """

    def __init__(self, table: dict) -> None:
        self.action_table = table["action"]
        self.goto_table   = table["goto"]

    def parse(self, tokens: list) -> dict:
        """Parse tokens and return the AST (no trace overhead)."""
        return self.parse_with_trace(tokens)["ast"]

    def parse_with_trace(self, tokens: list) -> dict:
    
        state_stack = Stack()
        ast_stack   = Stack()
        parse_stack = Stack()
        state_stack.push(0)

        lr_trace: list[dict] = []
        token_index = 0
        step_number = 0

        while True:
            current_state = state_stack.peek()
            current_token = tokens[token_index]
            lookahead_type = (
                "EOF" if current_token.token_type == "EOF" else current_token.token_type
            )

            action = self.action_table.get((current_state, lookahead_type))

            if action is None:
                error_detail = build_smart_syntax_error(
                    state=current_state,
                    action_table=self.action_table,
                    unexpected_type=lookahead_type,
                    unexpected_lexeme=current_token.lexeme,
                    line=current_token.line,
                    column=current_token.column,
                )
                raise CompilerError(error_detail.format_message())

            action_kind, action_payload = action
            step_number += 1
            stack_snapshot = state_stack.as_list()

            if action_kind == "shift":
                target_state = action_payload
                lr_trace.append({
                    "step":        step_number,
                    "state_stack": stack_snapshot,
                    "lookahead":   {"type": lookahead_type, "lexeme": current_token.lexeme},
                    "action":      f"shift; go to state {target_state}",
                })
                state_stack.push(target_state)
                ast_stack.push({
                    "token_type": current_token.token_type,
                    "lexeme":     current_token.lexeme,
                })
                parse_stack.push({
                    "kind":   "terminal",
                    "symbol": lookahead_type,
                    "lexeme": current_token.lexeme,
                })
                token_index += 1

            elif action_kind == "reduce":
                production_lhs, production_rhs = action_payload
                rhs_display = "ε" if len(production_rhs) == 0 else " ".join(production_rhs)
                lr_trace.append({
                    "step":        step_number,
                    "state_stack": stack_snapshot,
                    "lookahead":   {"type": lookahead_type, "lexeme": current_token.lexeme},
                    "action":      f"reduce {production_lhs} -> {rhs_display}",
                })

                ast_children   = []
                parse_children = []
                for _ in production_rhs:
                    state_stack.pop()
                    ast_children.insert(0,   ast_stack.pop())
                    parse_children.insert(0, parse_stack.pop())

                ast_node = reduce_ast(production_lhs, production_rhs, ast_children)
                parse_node = {
                    "kind":       "nonterminal",
                    "lhs":        production_lhs,
                    "rhs":        list(production_rhs),
                    "production": f"{production_lhs} -> {rhs_display}",
                    "children":   parse_children,
                }

                goto_state = self.goto_table.get((state_stack.peek(), production_lhs))
                if goto_state is None:
                    raise CompilerError(
                        f"LR parser: no GOTO entry for state {state_stack.peek()}"
                        f" on symbol '{production_lhs}'."
                    )
                state_stack.push(goto_state)
                ast_stack.push(ast_node)
                parse_stack.push(parse_node)

            elif action_kind == "accept":
                lr_trace.append({
                    "step":        step_number,
                    "state_stack": state_stack.as_list(),
                    "lookahead":   {"type": "EOF", "lexeme": "$"},
                    "action":      "accept",
                })
                final_ast = ast_stack.pop()
                parse_root = parse_stack.pop() if len(parse_stack) else None

                if final_ast.get("node") != "Program":
                    empty_program = {"node": "Program", "globals": []}
                    return {"ast": empty_program, "parse_tree": parse_root, "lr_trace": lr_trace}

                return {"ast": final_ast, "parse_tree": parse_root, "lr_trace": lr_trace}

            else:
                raise CompilerError(f"LR parser: unknown action kind '{action_kind}'.")
