from __future__ import annotations

import argparse
import json

from pathlib import Path

from config import BASE_DIR, DEFAULT_INPUT_FILE, OUTPUT_DIR
from grammar.lr1_table import build_lr1_table
from grammar.parsing_table import parse_grammar_file
from intermediate.optimizer import optimize_tac
from intermediate.tac import TACGenerator
from lexer.lexer import Lexer
from parser.parser import LRParser
from preprocessor.preprocessor import Preprocessor
from semantic.semantic import SemanticAnalyzer
from utils.error import CompilerError
from utils.helpers import write_json, write_text
from utils.input_paths import read_source_file
from codegen.asm_gen import tac_to_asm
from assembler.hte import asm_to_hte


def run_compiler(source_code: str) -> dict:
    grammar_path = BASE_DIR / "grammar" / "grammar.txt"
    grammar, start_symbol = parse_grammar_file(str(grammar_path))
    table = build_lr1_table(grammar, start_symbol)

    pre = Preprocessor()
    pre_result = pre.run(source_code)

    lexer = Lexer(pre_result.output_source)
    tokens = lexer.tokenize()

    parser = LRParser(table)
    parse_bundle = parser.parse_with_trace(tokens)
    ast = parse_bundle["ast"]
    parse_tree = parse_bundle["parse_tree"]
    lr_trace = parse_bundle["lr_trace"]

    semantic = SemanticAnalyzer()
    symbol_table = semantic.analyze(ast, includes=pre_result.includes)

    tac_generator = TACGenerator()
    tac = tac_generator.generate(ast)
    tac_optimized = optimize_tac(tac)

    asm_lines = tac_to_asm(tac_optimized)
    hte_text = asm_to_hte(asm_lines, program_name="LRCS", start_addr=0)

    write_json(OUTPUT_DIR / "tokens.json", [t.to_dict() for t in tokens])
    write_json(OUTPUT_DIR / "ast.json", ast)
    write_json(OUTPUT_DIR / "parse_tree.json", parse_tree)
    write_json(OUTPUT_DIR / "lr_trace.json", lr_trace)
    write_json(OUTPUT_DIR / "symbol_table.json", symbol_table)
    write_json(OUTPUT_DIR / "preprocessor.json", pre_result.to_dict())
    # run_result is produced separately by the GUI after the user provides stdin
    write_text(OUTPUT_DIR / "tac.txt", "\n".join(tac_optimized))
    write_text(OUTPUT_DIR / "program.asm", "\n".join(asm_lines) + "\n")
    write_text(OUTPUT_DIR / "program.obj", hte_text)

    includes = pre_result.includes

    return {
        "grammar_start_symbol": start_symbol,
        "includes": includes,
        "parser_kind": table.get("kind", "SLR(1)"),
        "states_count": len(
            {state for state, _ in table["action"].keys()} | {state for state, _ in table["goto"].keys()}
        ),
        "preprocessor": pre_result.to_dict(),
        "tokens": [t.to_dict() for t in tokens],
        "ast": ast,
        "parse_tree": parse_tree,
        "lr_trace": lr_trace,
        "symbol_table": symbol_table,
        "tac_raw": tac,
        "tac_optimized": tac_optimized,
        "run_result": None,
        "asm": asm_lines,
        "object_hte": hte_text,
    }


def format_compilation_details(result: dict) -> str:
    return (
        "=== CFG / Parsing ===\n"
        f"Start Symbol: {result['grammar_start_symbol']}\n"
        f"Parser: {result.get('parser_kind')}\n"
        f"Approx. Parser States: {result['states_count']}\n\n"
        "=== Preprocessor ===\n"
        f"{json.dumps(result.get('preprocessor'), indent=2)}\n\n"
        "=== Lexical Analysis (Tokens) ===\n"
        f"{json.dumps(result['tokens'], indent=2)}\n\n"
        "=== Syntax Analysis — Abstract Syntax Tree (AST) ===\n"
        f"{json.dumps(result['ast'], indent=2)}\n\n"
        "=== Syntax Analysis — Concrete Parse Tree ===\n"
        f"{json.dumps(result.get('parse_tree'), indent=2)}\n\n"
        "=== Syntax Analysis — LR Parser Trace (shift / reduce / accept) ===\n"
        f"{json.dumps(result.get('lr_trace'), indent=2)}\n\n"
        "=== Semantic Analysis (Symbol Table) ===\n"
        f"{json.dumps(result['symbol_table'], indent=2)}\n\n"
        "=== Intermediate Code (TAC - Raw) ===\n"
        f"{chr(10).join(result['tac_raw'])}\n\n"
        "=== Optimized TAC ===\n"
        f"{chr(10).join(result['tac_optimized'])}\n"
    )


def format_lr_trace_readable(trace: list[dict]) -> str:
    """Plain-text table of LR trace steps for the GUI."""
    lines: list[str] = []
    for row in trace:
        la = row.get("lookahead") or {}
        lines.append(
            f"Step {row.get('step')}: stack={row.get('state_stack')} | "
            f"lookahead={la.get('lexeme')!r} ({la.get('type')}) | {row.get('action')}"
        )
    return "\n".join(lines)


def main() -> None:
    arg_parser = argparse.ArgumentParser(
        description="C++ subset compiler: preprocessor → lexer → LR(1) parser → AST → semantics → TAC."
    )
    arg_parser.add_argument(
        "source",
        nargs="?",
        default=str(DEFAULT_INPUT_FILE),
        help="Input source file (.txt or .cpp)",
    )
    args = arg_parser.parse_args()

    try:
        source_code = read_source_file(Path(args.source))
        result = run_compiler(source_code)
        print("Compilation completed successfully.")
        print(f"Outputs written to: {OUTPUT_DIR}")
        print(f"Generated {len(result['tokens'])} tokens.")
    except CompilerError as exc:
        print(f"Compilation failed: {exc}")
        raise SystemExit(1) from exc
    except FileNotFoundError as exc:
        print(f"Input file not found: {args.source}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
