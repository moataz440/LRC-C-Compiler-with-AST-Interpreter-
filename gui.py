from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config import BASE_DIR, DEFAULT_INPUT_FILE, OUTPUT_DIR
from grammar.cfg_view import open_cfg_window
from gui.ast_to_tree import ast_to_tree
from gui.lr_visual import render_lr_trace
from gui.parse_to_tree import parse_to_tree
from gui.tree_canvas import render_tree
from main import format_compilation_details, format_lr_trace_readable, run_compiler
from utils.error import CompilerError
from utils.input_paths import read_source_file, validate_source_path


GRAMMAR_PATH = str(BASE_DIR / "grammar" / "grammar.txt")


# ── Friendly error formatter ──────────────────────────────────────────────────
def _make_friendly_error(raw: str) -> str:
    """
    Convert a raw CompilerError message into a beginner-friendly explanation.
    Keeps the original detail but adds a plain-English header.
    """
    msg = raw.strip()
    low = msg.lower()

    # ── Syntax errors ─────────────────────────────────────────────────────────
    if "syntax error" in low:
        header = " Syntax Error — your code has a grammar mistake."
        tip = ""
        if "missing" in low and ";" in msg:
            tip = "\n Tip: You probably forgot a semicolon ';' at the end of a statement."
        elif "'}'" in msg or "missing a closing brace" in low:
            tip = "\n Tip: A closing brace '}' is missing. Check that every '{' has a matching '}'."
        elif "'('" in msg or "missing a closing parenthesis" in low:
            tip = "\n Tip: A closing parenthesis ')' is missing."
        elif "else" in low:
            tip = "\n Tip: This 'else' doesn't match an 'if'. Check your braces."
        elif "expected:" in low:
            tip = "\n Tip: Check the token just before the marked line."
        return f"{header}\n\n{msg}{tip}"

    # ── Lexer / unknown character errors ─────────────────────────────────────
    if "unknown character" in low or "unexpected character" in low or "lexer" in low:
        return (
            f" Unknown Character — your code contains a symbol the compiler doesn't recognise.\n\n"
            f"{msg}\n"
            " Tip: Look for typos, copy-paste artefacts, or unsupported symbols."
        )

    # ── Type errors ───────────────────────────────────────────────────────────
    if "type" in low and ("mismatch" in low or "cannot" in low or "incompatible" in low):
        return (
            f" Type Error — you are mixing incompatible types.\n\n"
            f"{msg}\n"
            " Tip: Make sure both sides of an assignment or expression have the same type (e.g. int with int)."
        )

    # ── Undeclared / undefined variable ──────────────────────────────────────
    if "undeclared" in low or ("undefined" in low and "variable" in low) or "not declared" in low:
        return (
            f" Undeclared Variable — you used a variable before declaring it.\n\n"
            f"{msg}\n"
            " Tip: Add a declaration like 'int x;' before using 'x'."
        )

    # ── Redeclaration ─────────────────────────────────────────────────────────
    if "redeclar" in low or "already declared" in low or "duplicate" in low:
        return (
            f" Redeclaration — a variable or function is declared more than once.\n\n"
            f"{msg}\n"
            " Tip: Remove or rename the duplicate declaration."
        )

    # ── Return errors ─────────────────────────────────────────────────────────
    if "return" in low and ("missing" in low or "no return" in low or "expected" in low):
        return (
            f" Missing Return — a function that should return a value is missing a 'return' statement.\n\n"
            f"{msg}\n"
            " Tip: Add 'return <value>;' at the end of your function."
        )

    # ── Runtime: cin / input errors ───────────────────────────────────────────
    if "cin" in low or "end of input" in low or "stdin" in low:
        return (
            f" Input Error — the program tried to read more input than was provided.\n\n"
            f"{msg}\n"
            " Tip: Type a value in the cin input box at the bottom of the terminal and press Enter."
        )

    # ── Runtime: division by zero ─────────────────────────────────────────────
    if "division by zero" in low or "divide by zero" in low:
        return (
            f" Division by Zero — your program tried to divide a number by 0.\n\n"
            f"{msg}\n"
            " Tip: Add a check (if divisor != 0) before dividing."
        )

    # ── Runtime: variable used before declaration ─────────────────────────────
    if "runtime error" in low and "used before declaration" in low:
        return (
            f" Variable Not Initialised — a variable was used before being given a value.\n\n"
            f"{msg}\n"
            " Tip: Make sure the variable is declared and assigned a value before you use it."
        )

    # ── File not found ────────────────────────────────────────────────────────
    if "file not found" in low or "no such file" in low:
        return (
            f" File Not Found — the source file could not be opened.\n\n"
            f"{msg}\n"
            " Tip: Check that the file path in the Editor tab is correct."
        )

    # ── Fallback: return raw message with a generic header ───────────────────
    return f" Compiler Error\n\n{msg}\n\n Check the line and column numbers shown above for the exact location."

# ── Colour tokens ────────────────────────────────────────────────────────────
SIDEBAR_BG   = "#1a1f2e"
SIDEBAR_SEL  = "#252d3d"
SIDEBAR_HVR  = "#1e2535"
ACCENT_BLUE  = "#4f7de8"
ACCENT_GREEN = "#3ecf8e"
ACCENT_AMBER = "#f5a623"
ACCENT_RED   = "#e05c5c"
MAIN_BG      = "#151923"
PANEL_BG     = "#1c2130"
PANEL_BORDER = "#2a3045"
TERM_BG      = "#0d1117"
TEXT_PRI     = "#e8eaf0"
TEXT_SEC     = "#7a84a0"
TEXT_DIM     = "#505870"
TEXT_GREEN   = "#4ec9b0"
TEXT_AMBER   = "#ce9178"
TEXT_CODE    = "#d4d4d4"


class MaximizedWindow(ctk.CTkToplevel):
    def __init__(self, parent, title: str, build_fn, is_dark_fn):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.resizable(True, True)
        self._is_dark_fn = is_dark_fn
        self.configure(fg_color=MAIN_BG)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(self, corner_radius=0, fg_color=PANEL_BG, height=46,
                           border_width=1, border_color=PANEL_BORDER)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bar, text=title, font=ctk.CTkFont("Consolas", size=14, weight="bold"),
            text_color=TEXT_PRI,
        ).grid(row=0, column=0, padx=16, sticky="w")

        ctk.CTkButton(
            bar, text="X  Close", width=100, height=30, command=self.destroy,
            fg_color="transparent", border_width=1, border_color=PANEL_BORDER,
            text_color=TEXT_SEC, hover_color=SIDEBAR_SEL,
        ).grid(row=0, column=1, padx=12, pady=8)

        content = ctk.CTkFrame(self, corner_radius=0, fg_color=MAIN_BG)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._canvas_ref = None
        self._lr_ref = None
        build_fn(content, self)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.lift()
        self.focus_force()


class CompilerGUI(ctk.CTk):
    """LR Studio - sidebar-navigation layout matching the LR Studio design."""

    NAV_ITEMS = [
        ("Editor",         "workspace", "editor"),
        ("Grammar (CFG)",  "workspace", "cfg"),
        ("Summary",        "results",   "summary"),
        ("Tokens",         "results",   "tokens"),
        ("AST",            "results",   "ast"),
        ("Parse Tree",     "results",   "parse_tree"),
        ("LR Trace",       "results",   "lr_trace"),
        ("Symbol Table",   "results",   "sym_table"),
        ("TAC",            "results",   "tac"),
        ("Assembly",       "results",   "assembly"),
        ("Object Code",    "results",   "object_code"),
        ("Program Output", "results",   "program_output"),
    ]

    NAV_ICONS = {
        "editor":         "\\",
        "cfg":            "o",
        "summary":        ">",
        "tokens":         "^",
        "ast":            "@",
        "parse_tree":     "@",
        "lr_trace":       "=",
        "sym_table":      "~",
        "tac":            "*",
        "assembly":       ".",
        "object_code":    "#",
        "program_output": ">",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("LR Studio")
        self.geometry("1280x860")
        self.minsize(1000, 680)
        self.configure(fg_color=MAIN_BG)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.file_path_var   = ctk.StringVar(value=str(DEFAULT_INPUT_FILE))
        self.status_var      = ctk.StringVar(value="Ready.")
        self.last_result: dict | None = None
        self._active_panel   = "program_output"
        self._display_mode   = "text"
        self._tree_canvas    = None
        self._lr_text_widget = None
        self.input_mode_var  = ctk.StringVar(value="File")
        self.editor_text: ctk.CTkTextbox | None = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        self._nav_select("program_output")

    # ─────────────────────────────────────────────────────────────────────
    # Sidebar
    # ─────────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=SIDEBAR_BG, width=196)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        self._sidebar = sidebar

        # Logo
        logo_row = ctk.CTkFrame(sidebar, fg_color="transparent", height=52)
        logo_row.grid(row=0, column=0, sticky="ew")
        logo_row.grid_propagate(False)

        logo_box = ctk.CTkFrame(logo_row, fg_color=ACCENT_BLUE, width=26, height=26, corner_radius=5)
        logo_box.place(x=12, y=13)
        ctk.CTkLabel(logo_box, text="LR",
                     font=ctk.CTkFont("Consolas", size=10, weight="bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(logo_row, text="LR Studio",
                     font=ctk.CTkFont("Consolas", size=14, weight="bold"),
                     text_color=TEXT_PRI).place(x=46, y=15)

        ctk.CTkFrame(sidebar, height=1, fg_color=PANEL_BORDER).grid(
            row=1, column=0, sticky="ew")

        row_idx = 2
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

        last_section = None
        for (label, section, key) in self.NAV_ITEMS:
            if section != last_section:
                section_text = "WORKSPACE" if section == "workspace" else "COMPILATION RESULTS"
                ctk.CTkLabel(sidebar, text=section_text,
                             font=ctk.CTkFont("Consolas", size=9, weight="bold"),
                             text_color=TEXT_DIM).grid(
                    row=row_idx, column=0, sticky="w", padx=14, pady=(8, 1))
                row_idx += 1
                last_section = section

            btn = ctk.CTkButton(
                sidebar,
                text=f"  {label}",
                anchor="w",
                height=30,
                corner_radius=5,
                fg_color="transparent",
                text_color=TEXT_SEC,
                hover_color=SIDEBAR_HVR,
                font=ctk.CTkFont("Consolas", size=12),
                command=lambda k=key: self._nav_select(k),
            )
            btn.grid(row=row_idx, column=0, sticky="ew", padx=6, pady=1)
            self._nav_buttons[key] = btn
            row_idx += 1

        sidebar.grid_rowconfigure(row_idx, weight=1)
        row_idx += 1

        ctk.CTkFrame(sidebar, height=1, fg_color=PANEL_BORDER).grid(
            row=row_idx, column=0, sticky="ew")
        row_idx += 1

        # Bottom status line
        bottom_row = ctk.CTkFrame(sidebar, fg_color="transparent", height=28)
        bottom_row.grid(row=row_idx, column=0, sticky="ew")
        bottom_row.grid_propagate(False)

        self._compiler_label = ctk.CTkLabel(
            bottom_row,
            text="LR(1) Compiler",
            font=ctk.CTkFont("Consolas", size=10),
            text_color=TEXT_DIM,
        )
        self._compiler_label.place(x=12, y=6)

    def _nav_select(self, key: str) -> None:
        self._active_panel = key
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=SIDEBAR_SEL, text_color=TEXT_PRI)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SEC)
        self._show_panel(key)

    # ─────────────────────────────────────────────────────────────────────
    # Main area
    # ─────────────────────────────────────────────────────────────────────

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=MAIN_BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        self._main_frame = main

        # Top bar
        topbar = ctk.CTkFrame(main, corner_radius=0, fg_color=PANEL_BG, height=46,
                              border_width=1, border_color=PANEL_BORDER)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        self._topbar_title = ctk.CTkLabel(
            topbar, text="Program Output",
            font=ctk.CTkFont("Consolas", size=13, weight="bold"),
            text_color=TEXT_PRI,
        )
        self._topbar_title.grid(row=0, column=0, padx=20, sticky="w")

        right = ctk.CTkFrame(topbar, fg_color="transparent")
        right.grid(row=0, column=1, padx=12, sticky="e")

        self._sample_var = ctk.StringVar(value="Load sample...")
        ctk.CTkOptionMenu(
            right,
            variable=self._sample_var,
            values=["test1.txt", "test2.txt", "test_for_loop.txt", "sample.cpp"],
            command=self._load_sample,
            width=140, height=30,
            fg_color=PANEL_BG,
            button_color=SIDEBAR_SEL,
            button_hover_color=SIDEBAR_HVR,
            text_color=TEXT_SEC,
            font=ctk.CTkFont("Consolas", size=11),
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            right, text="Compile", width=100, height=30,
            command=self._compile,
            fg_color=ACCENT_BLUE,
            hover_color="#3d6bd4",
            text_color="white",
            font=ctk.CTkFont("Consolas", size=12, weight="bold"),
        ).grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(
            right, text="▶ Run", width=88, height=30,
            command=self._compile_and_run,
            fg_color=ACCENT_GREEN,
            hover_color="#30b87a",
            text_color="white",
            font=ctk.CTkFont("Consolas", size=12, weight="bold"),
        ).grid(row=0, column=2)

        # Content panels container
        content = ctk.CTkFrame(main, corner_radius=0, fg_color=MAIN_BG)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        self._content_frame = content

        self._panels: dict[str, ctk.CTkFrame] = {}
        self._build_all_panels(content)

        # Bottom status bar
        statusbar = ctk.CTkFrame(main, corner_radius=0, fg_color=PANEL_BG, height=28,
                                 border_width=1, border_color=PANEL_BORDER)
        statusbar.grid(row=2, column=0, sticky="ew")
        statusbar.grid_propagate(False)
        statusbar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(statusbar, textvariable=self.status_var,
                     font=ctk.CTkFont("Consolas", size=10),
                     text_color=TEXT_DIM, anchor="w").grid(
            row=0, column=0, padx=14, sticky="w")

        self._token_count_var = ctk.StringVar(value="")
        ctk.CTkLabel(statusbar, textvariable=self._token_count_var,
                     font=ctk.CTkFont("Consolas", size=10),
                     text_color=TEXT_DIM, anchor="e").grid(
            row=0, column=1, padx=14, sticky="e")

    def _build_all_panels(self, parent) -> None:
        self._build_panel_editor(parent)
        self._build_panel_program_output(parent)
        self._build_panel_summary(parent)
        self._build_panel_cfg(parent)
        for key, title in [
            ("tokens",      "Tokens"),
            ("ast",         "AST"),
            ("parse_tree",  "Parse Tree"),
            ("lr_trace",    "LR Trace"),
            ("sym_table",   "Symbol Table"),
            ("tac",         "TAC"),
            ("assembly",    "Assembly"),
            ("object_code", "Object Code"),
        ]:
            self._build_panel_generic(key, parent, title)

    def _make_panel(self, key: str, parent) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, corner_radius=0, fg_color=MAIN_BG)
        f.grid(row=0, column=0, sticky="nsew")
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=1)
        f.grid_remove()
        self._panels[key] = f
        return f

    def _show_panel(self, key: str) -> None:
        titles = {
            "editor":         "Editor",
            "cfg":            "Grammar (CFG)",
            "summary":        "Summary",
            "tokens":         "Tokens",
            "ast":            "AST",
            "parse_tree":     "Parse Tree",
            "lr_trace":       "LR Trace",
            "sym_table":      "Symbol Table",
            "tac":            "TAC",
            "assembly":       "Assembly",
            "object_code":    "Object Code",
            "program_output": "Program Output",
        }
        self._topbar_title.configure(text=titles.get(key, key))
        for k, panel in self._panels.items():
            if k == key:
                panel.grid()
            else:
                panel.grid_remove()
        if key not in ("editor", "cfg", "program_output", "summary"):
            self._refresh_data_panel(key)

    # ─────────────────────────────────────────────────────────────────────
    # Panel builders
    # ─────────────────────────────────────────────────────────────────────

    def _build_panel_editor(self, parent) -> None:
        p = self._make_panel("editor", parent)
        p.grid_rowconfigure(1, weight=1)

        tb = ctk.CTkFrame(p, fg_color=PANEL_BG, height=42, corner_radius=0,
                          border_width=1, border_color=PANEL_BORDER)
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_propagate(False)

        ctk.CTkButton(
            tb, text="Browse", width=80, height=26,
            command=self._browse_file,
            fg_color=SIDEBAR_SEL, hover_color=SIDEBAR_HVR,
            text_color=TEXT_SEC, font=ctk.CTkFont("Consolas", size=11),
        ).pack(side="left", padx=(10, 4), pady=8)

        ctk.CTkEntry(
            tb, textvariable=self.file_path_var,
            height=26, width=320,
            fg_color=MAIN_BG, border_color=PANEL_BORDER,
            text_color=TEXT_SEC, font=ctk.CTkFont("Consolas", size=11),
        ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            tb, text="Load file", width=76, height=26,
            command=self._load_file_to_editor,
            fg_color="transparent", border_width=1, border_color=PANEL_BORDER,
            text_color=TEXT_SEC, hover_color=SIDEBAR_HVR,
            font=ctk.CTkFont("Consolas", size=11),
        ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            tb, text="Output folder", width=106, height=26,
            command=self._open_output_folder,
            fg_color="transparent", border_width=1, border_color=PANEL_BORDER,
            text_color=TEXT_SEC, hover_color=SIDEBAR_HVR,
            font=ctk.CTkFont("Consolas", size=11),
        ).pack(side="left", padx=4, pady=8)

        self.save_btn = ctk.CTkButton(
            tb, text="Save report", width=92, height=26,
            command=self._save_details_report, state="disabled",
            fg_color="transparent", border_width=1, border_color=PANEL_BORDER,
            text_color=TEXT_DIM, hover_color=SIDEBAR_HVR,
            font=ctk.CTkFont("Consolas", size=11),
        )
        self.save_btn.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            tb, text="Run", width=60, height=26,
            command=self._run,
            fg_color=ACCENT_GREEN, hover_color="#30b87a",
            text_color="white", font=ctk.CTkFont("Consolas", size=11, weight="bold"),
        ).pack(side="right", padx=10, pady=8)

        # Editor body
        editor_body = ctk.CTkFrame(p, fg_color=TERM_BG, corner_radius=0)
        editor_body.grid(row=1, column=0, sticky="nsew")
        editor_body.grid_columnconfigure(0, weight=1)
        editor_body.grid_rowconfigure(0, weight=1)

        self.editor_text = ctk.CTkTextbox(
            editor_body,
            font=ctk.CTkFont("Consolas", size=13),
            fg_color=TERM_BG,
            text_color=TEXT_CODE,
            border_width=0,
            corner_radius=0,
        )
        self.editor_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _build_panel_cfg(self, parent) -> None:
        p = self._make_panel("cfg", parent)

        frame = ctk.CTkFrame(p, fg_color="transparent")
        frame.place(relx=0.5, rely=0.4, anchor="center")

        ctk.CTkLabel(
            frame, text="Grammar (CFG)",
            font=ctk.CTkFont("Consolas", size=20, weight="bold"),
            text_color=TEXT_PRI,
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            frame, text="View the context-free grammar in a dedicated window.",
            font=ctk.CTkFont("Consolas", size=12),
            text_color=TEXT_SEC,
        ).pack(pady=(0, 18))

        ctk.CTkButton(
            frame, text="Open CFG Viewer", width=200, height=38,
            command=self._open_cfg_window,
            fg_color=ACCENT_BLUE, hover_color="#3d6bd4",
            text_color="white", font=ctk.CTkFont("Consolas", size=13, weight="bold"),
        ).pack()

    def _build_panel_program_output(self, parent) -> None:
        p = self._make_panel("program_output", parent)
        p.grid_rowconfigure(0, weight=1)

        # ── Interactive Terminal card (fills the whole panel) ────────────────
        term_card = ctk.CTkFrame(
            p, fg_color=PANEL_BG, corner_radius=10,
            border_width=1, border_color=PANEL_BORDER,
        )
        term_card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        term_card.grid_columnconfigure(0, weight=1)
        term_card.grid_rowconfigure(1, weight=1)

        # Traffic-lights header row
        lights_row = ctk.CTkFrame(term_card, fg_color="transparent", height=30)
        lights_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        lights_row.grid_propagate(False)

        for col in ["#ff5f56", "#ffbd2e", "#27c93f"]:
            dot = tk.Frame(lights_row, bg=col, width=11, height=11)
            dot.pack(side="left", padx=2)

        ctk.CTkLabel(
            lights_row, text="interactive terminal",
            font=ctk.CTkFont("Consolas", size=11),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(10, 0))

        self._exit_code_var = ctk.StringVar(value="")
        self._exit_label = ctk.CTkLabel(
            lights_row, textvariable=self._exit_code_var,
            font=ctk.CTkFont("Consolas", size=11, weight="bold"),
            text_color=TEXT_AMBER,
        )
        self._exit_label.pack(side="right", padx=14)

        # Terminal body: read-only output textbox
        term_inner = ctk.CTkFrame(term_card, fg_color=TERM_BG, corner_radius=6)
        term_inner.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 0))
        term_inner.grid_columnconfigure(0, weight=1)
        term_inner.grid_rowconfigure(0, weight=1)

        self.program_output_text = ctk.CTkTextbox(
            term_inner,
            font=ctk.CTkFont("Consolas", size=13),
            fg_color=TERM_BG, text_color=TEXT_CODE,
            border_width=0, corner_radius=0,
            wrap="word",
            state="disabled",
        )
        self.program_output_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))

        # stdin input row at bottom of terminal
        input_bar = ctk.CTkFrame(term_inner, fg_color="#0a0e14", corner_radius=0, height=38)
        input_bar.grid(row=1, column=0, sticky="ew", padx=0, pady=(4, 0))
        input_bar.grid_propagate(False)
        input_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            input_bar, text=" cin ▶",
            font=ctk.CTkFont("Consolas", size=12, weight="bold"),
            text_color=TEXT_GREEN, width=56,
        ).grid(row=0, column=0, padx=(8, 4), pady=6, sticky="w")

        self.stdin_entry = ctk.CTkEntry(
            input_bar,
            font=ctk.CTkFont("Consolas", size=13),
            fg_color=TERM_BG, border_color="#2a3a2a",
            text_color=TEXT_CODE, height=26,
            placeholder_text="type input for cin here and press Enter…",
            placeholder_text_color=TEXT_DIM,
        )
        self.stdin_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4), pady=6)
        self.stdin_entry.bind("<Return>", self._on_stdin_enter)
        self.stdin_entry.configure(state="disabled")  # enabled only when program waits for input

        send_btn = ctk.CTkButton(
            input_bar, text="Send", width=56, height=26,
            command=self._on_stdin_send,
            fg_color=ACCENT_GREEN, hover_color="#30b87a",
            text_color="white", font=ctk.CTkFont("Consolas", size=11, weight="bold"),
        )
        send_btn.grid(row=0, column=2, padx=(0, 8), pady=6)
        self._stdin_send_btn = send_btn
        self._stdin_send_btn.configure(state="disabled")

        # State for interactive execution
        self._run_thread: threading.Thread | None = None
        self._stdin_queue: queue.Queue = queue.Queue()
        self._run_complete = False
        # Keep backward-compat: old code that writes self.stdin_text still works
        self.stdin_text = None
        self.run_text = None

    def _build_panel_summary(self, parent) -> None:
        p = self._make_panel("summary", parent)
        p.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(p, fg_color=MAIN_BG, corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(scroll, fg_color=PANEL_BG, corner_radius=10,
                            border_width=1, border_color=PANEL_BORDER)
        card.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(card, text="Compilation Summary",
                     font=ctk.CTkFont("Consolas", size=14, weight="bold"),
                     text_color=TEXT_PRI).pack(anchor="w", padx=16, pady=(12, 4))

        self.summary_text = ctk.CTkTextbox(
            card, height=200,
            font=ctk.CTkFont("Consolas", size=12),
            fg_color=PANEL_BG, text_color=TEXT_CODE, border_width=0, corner_radius=0,
        )
        self.summary_text.pack(fill="x", padx=12, pady=(0, 12))
        self.summary_text.insert("1.0", "No compilation yet.")
        self.summary_text.configure(state="disabled")

    def _build_panel_generic(self, key: str, parent, title: str) -> None:
        p = self._make_panel(key, parent)
        supports_visual = key in ("ast", "parse_tree", "lr_trace")

        if supports_visual:
            tb = ctk.CTkFrame(p, fg_color=PANEL_BG, height=40, corner_radius=0,
                              border_width=1, border_color=PANEL_BORDER)
            tb.grid(row=0, column=0, sticky="ew")
            tb.grid_propagate(False)
            p.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(tb, text=title,
                         font=ctk.CTkFont("Consolas", size=12, weight="bold"),
                         text_color=TEXT_PRI).pack(side="left", padx=14)

            ctk.CTkButton(
                tb, text="  Fullscreen", width=110, height=26,
                command=lambda k=key, t=title: self._open_fullscreen(k, t),
                fg_color="transparent", border_width=1, border_color=PANEL_BORDER,
                text_color=TEXT_SEC, hover_color=SIDEBAR_HVR,
                font=ctk.CTkFont("Consolas", size=11),
            ).pack(side="right", padx=(4, 10))

            seg = ctk.CTkSegmentedButton(
                tb, values=["Text", "Visual"],
                command=self._on_display_mode,
                width=150, height=26,
                fg_color=MAIN_BG, selected_color=ACCENT_BLUE,
                selected_hover_color="#3d6bd4",
                unselected_color=MAIN_BG, unselected_hover_color=SIDEBAR_SEL,
                text_color=TEXT_SEC,
                font=ctk.CTkFont("Consolas", size=11),
            )
            seg.set("Text")
            seg.pack(side="right", padx=4)
            p._mode_seg = seg
            body_row = 1
        else:
            tb = ctk.CTkFrame(p, fg_color=PANEL_BG, height=40, corner_radius=0,
                              border_width=1, border_color=PANEL_BORDER)
            tb.grid(row=0, column=0, sticky="ew")
            tb.grid_propagate(False)
            p.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(tb, text=title,
                         font=ctk.CTkFont("Consolas", size=12, weight="bold"),
                         text_color=TEXT_PRI).pack(side="left", padx=14)

            ctk.CTkButton(
                tb, text="  Fullscreen", width=110, height=26,
                command=lambda k=key, t=title: self._open_fullscreen(k, t),
                fg_color="transparent", border_width=1, border_color=PANEL_BORDER,
                text_color=TEXT_SEC, hover_color=SIDEBAR_HVR,
                font=ctk.CTkFont("Consolas", size=11),
            ).pack(side="right", padx=(4, 10))

            body_row = 1

        body = ctk.CTkFrame(p, fg_color=MAIN_BG, corner_radius=0)
        body.grid(row=body_row, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        p._body_frame = body

        txt = ctk.CTkTextbox(
            body, font=ctk.CTkFont("Consolas", size=12),
            fg_color=PANEL_BG, text_color=TEXT_CODE, border_width=0, corner_radius=0,
            wrap="none",
        )
        txt.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        txt.insert("1.0", f"Compile first to see {title} data.")
        txt.configure(state="disabled")
        p._text_widget = txt

        visual_host = ctk.CTkFrame(body, fg_color="transparent", corner_radius=8)
        visual_host.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        visual_host.grid_columnconfigure(0, weight=1)
        visual_host.grid_rowconfigure(0, weight=1)
        visual_host.grid_remove()
        p._visual_host = visual_host

        p._data_key = key
        p._supports_visual = supports_visual
        p._current_mode = "text"

    # ─────────────────────────────────────────────────────────────────────
    # Data refresh
    # ─────────────────────────────────────────────────────────────────────

    def _refresh_data_panel(self, key: str) -> None:
        p = self._panels.get(key)
        if p is None or not hasattr(p, "_data_key"):
            return
        text = self._get_panel_text(p._data_key)
        supports = getattr(p, "_supports_visual", False)
        mode = self._display_mode if supports else "text"

        if mode == "text":
            if hasattr(p, "_visual_host"):
                p._visual_host.grid_remove()
            if hasattr(p, "_text_widget"):
                p._text_widget.grid()
            self._set_panel_text(p, text)
        else:
            if hasattr(p, "_text_widget"):
                p._text_widget.grid_remove()
            if hasattr(p, "_visual_host"):
                p._visual_host.grid()
                self._build_visual_in(p._visual_host, p._data_key)

    def _set_panel_text(self, p, text: str) -> None:
        if not hasattr(p, "_text_widget"):
            return
        tb = p._text_widget
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.insert("1.0", text)
        tb.configure(state="disabled")

    def _get_panel_text(self, data_key: str) -> str:
        r = self.last_result
        if r is None:
            return "Compile first to see data."
        if data_key == "tokens":
            return self._build_lex_table_text(r.get("tokens") or [])
        if data_key == "ast":
            return json.dumps(r.get("ast"), indent=2)
        if data_key == "parse_tree":
            return json.dumps(r.get("parse_tree"), indent=2)
        if data_key == "lr_trace":
            trace = r.get("lr_trace") or []
            return (
                "=== LR parser trace (readable) ===\n"
                f"{format_lr_trace_readable(trace)}\n\n"
                "=== LR parser trace (JSON) ===\n"
                f"{json.dumps(trace, indent=2)}"
            )
        if data_key == "sym_table":
            return self._build_sym_table_text(r)
        if data_key == "tac":
            raw = r.get("tac_raw") or []
            opt = r.get("tac_optimized") or []
            return (
                "=== Raw three-address code ===\n"
                + ("\n".join(raw) or "(empty)")
                + "\n\n=== Optimized three-address code ===\n"
                + ("\n".join(opt) or "(empty)")
            )
        if data_key == "assembly":
            asm = r.get("asm") or []
            return "\n".join(asm) if asm else "(No assembly output — compile first.)"
        if data_key == "object_code":
            hte = r.get("object_hte") or ""
            return hte or "(No object code — compile first.)"
        return format_compilation_details(r)

    def _build_visual_in(self, host: ctk.CTkFrame, data_key: str) -> None:
        for w in host.winfo_children():
            w.destroy()
        r = self.last_result
        dark = self._is_dark
        if data_key == "ast":
            t = ast_to_tree(r.get("ast"))
            if t:
                render_tree(host, t, dark)
            else:
                ctk.CTkLabel(host, text="(Could not build AST tree.)",
                             text_color=TEXT_SEC).grid()
        elif data_key == "parse_tree":
            t = parse_to_tree(r.get("parse_tree"))
            if t:
                render_tree(host, t, dark)
            else:
                ctk.CTkLabel(host, text="(No parse tree.)", text_color=TEXT_SEC).grid()
        elif data_key == "lr_trace":
            render_lr_trace(host, r.get("lr_trace") or [], dark)
        else:
            ctk.CTkLabel(host,
                         text="Visual mode only available for AST, Parse Tree, LR Trace.",
                         text_color=TEXT_SEC).grid()

    def _on_display_mode(self, value: str) -> None:
        self._display_mode = "text" if value == "Text" else "visual"
        key = self._active_panel
        if key in self._panels:
            self._refresh_data_panel(key)

    # ─────────────────────────────────────────────────────────────────────
    # CFG / Theme
    # ─────────────────────────────────────────────────────────────────────

    def _open_cfg_window(self) -> None:
        try:
            open_cfg_window(self, GRAMMAR_PATH, self._is_dark)
        except Exception as exc:
            messagebox.showerror("CFG Error", str(exc))

    def _is_dark(self) -> bool:
        return True

    # ─────────────────────────────────────────────────────────────────────
    # File helpers
    # ─────────────────────────────────────────────────────────────────────

    def _browse_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select source file",
            filetypes=[("C++ / text", "*.cpp *.txt"), ("All Files", "*.*")],
            initialdir=str(Path.cwd()),
        )
        if selected:
            self.file_path_var.set(selected)

    def _load_file_to_editor(self) -> None:
        if not self.editor_text:
            return
        source_path = Path(self.file_path_var.get()).expanduser()
        if not source_path.exists():
            messagebox.showerror("File Error", f"File not found:\n{source_path}")
            return
        try:
            validate_source_path(source_path)
        except CompilerError as exc:
            messagebox.showerror("File Error", str(exc))
            return
        self.editor_text.delete("1.0", "end")
        self.editor_text.insert("1.0", read_source_file(source_path))
        self._nav_select("editor")

    def _load_sample(self, name: str) -> None:
        if name.startswith("Load"):
            return
        sample_path = BASE_DIR / "tests" / name
        if sample_path.exists():
            self.file_path_var.set(str(sample_path))
            if self.editor_text:
                try:
                    validate_source_path(sample_path)
                    self.editor_text.delete("1.0", "end")
                    self.editor_text.insert("1.0", read_source_file(sample_path))
                except Exception:
                    pass
        self._sample_var.set("Load sample...")

    # ─────────────────────────────────────────────────────────────────────
    # Compile / Run
    # ─────────────────────────────────────────────────────────────────────

    def _open_fullscreen(self, key: str, title: str) -> None:
        """Open a fullscreen window showing the current panel content."""
        def build_fn(content_frame, win):
            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_rowconfigure(0, weight=1)

            p = self._panels.get(key)
            supports_visual = p is not None and getattr(p, "_supports_visual", False)
            current_mode = self._display_mode if supports_visual else "text"

            if current_mode == "visual" and supports_visual:
                host = ctk.CTkFrame(content_frame, fg_color="transparent", corner_radius=8)
                host.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
                host.grid_columnconfigure(0, weight=1)
                host.grid_rowconfigure(0, weight=1)
                self._build_visual_in(host, key)
            else:
                text = self._get_panel_text(key)
                tb = ctk.CTkTextbox(
                    content_frame,
                    font=ctk.CTkFont("Consolas", size=13),
                    fg_color=PANEL_BG, text_color=TEXT_CODE,
                    border_width=0, corner_radius=0, wrap="none",
                )
                tb.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
                tb.insert("1.0", text)
                tb.configure(state="disabled")

        MaximizedWindow(self, title, build_fn, self._is_dark)

    # ─────────────────────────────────────────────────────────────────────
    # Helper: get source code from editor or file
    # ─────────────────────────────────────────────────────────────────────
    def _get_source(self) -> tuple[str, str]:
        """Return (source_code, label). Raises CompilerError on failure."""
        source_code = ""
        input_label = ""
        if self.editor_text:
            editor_content = self.editor_text.get("1.0", "end").rstrip()
            if editor_content.strip():
                source_code = editor_content
                input_label = "(Editor)"
        if not source_code:
            source_path = Path(self.file_path_var.get()).expanduser()
            if not source_path.exists():
                raise CompilerError(f"File not found:\n{source_path}")
            validate_source_path(source_path)
            source_code = read_source_file(source_path)
            input_label = str(source_path)
        return source_code, input_label

    def _apply_compile_result(self, result: dict, input_label: str) -> None:
        """Populate GUI after a successful compilation."""
        self.last_result = result
        if hasattr(self, "save_btn"):
            self.save_btn.configure(state="normal", text_color=TEXT_SEC)

        ast = result.get("ast") or {}
        globals_list = ast.get("globals") if ast.get("node") == "Program" else []
        n_fn    = sum(1 for g in globals_list if isinstance(g, dict) and g.get("node") == "Function")
        n_using = sum(1 for g in globals_list if isinstance(g, dict) and g.get("node") == "UsingNamespace")
        n_gdecl = sum(1 for g in globals_list if isinstance(g, dict) and g.get("node") == "GlobalDecl")

        token_count = len(result["tokens"])
        self._token_count_var.set(f"{token_count} tokens")

        summary = (
            "Compilation succeeded.\n"
            f"Input: {input_label}\n"
            f"Tokens: {token_count}\n"
            f"Top-level items: {len(globals_list)} "
            f"({n_fn} functions, {n_using} using-namespace, {n_gdecl} global decls)\n"
            f"LR trace steps: {len(result.get('lr_trace') or [])}\n"
            f"Optimized TAC lines: {len(result['tac_optimized'])}\n"
            f"Output: {OUTPUT_DIR}"
        )
        self._set_summary(summary)

    def _handle_compile_error(self, exc: Exception) -> None:
        """Show a beginner-friendly error dialog and update the GUI."""
        raw = str(exc)
        friendly = _make_friendly_error(raw)
        messagebox.showerror("Compilation Error", friendly)
        self._set_summary(f"Compilation failed.\n\n{friendly}")
        self.status_var.set("Compilation failed.")
        self.last_result = None
        if hasattr(self, "save_btn"):
            self.save_btn.configure(state="disabled", text_color=TEXT_DIM)
        self._terminal_append("\n[Compilation error]\n" + friendly + "\n", color="error")
        self._token_count_var.set("")

    def _compile(self) -> None:
        try:
            source_code, input_label = self._get_source()
            result = run_compiler(source_code)
        except CompilerError as exc:
            self._handle_compile_error(exc)
            self._nav_select("program_output")
            return

        self._apply_compile_result(result, input_label)
        # Reset terminal
        self._terminal_reset()
        self._terminal_append("$ Compile succeeded. Press ▶ Run (or use the Run button in the Editor tab) to execute.\n", color="info")
        self.status_var.set("Compilation succeeded. Press ▶ Run to execute.")
        self._nav_select("program_output")

    def _compile_and_run(self) -> None:
        """Compile then immediately run in one click."""
        try:
            source_code, input_label = self._get_source()
            result = run_compiler(source_code)
        except CompilerError as exc:
            self._handle_compile_error(exc)
            self._nav_select("program_output")
            return

        self._apply_compile_result(result, input_label)
        self._terminal_reset()
        self._terminal_append("$ Compiled OK — running...\n", color="info")
        self.status_var.set("Running…")
        self._nav_select("program_output")
        self.after(50, self._start_run_thread)

    def _run(self) -> None:
        if not self.last_result:
            messagebox.showinfo("Run", "Compile first.")
            return
        if self._run_thread and self._run_thread.is_alive():
            messagebox.showinfo("Already running", "The program is still running.")
            return
        self._terminal_reset()
        self._terminal_append("$ ./program\n", color="prompt")
        self.status_var.set("Running…")
        self._nav_select("program_output")
        self.after(50, self._start_run_thread)

    def _start_run_thread(self) -> None:
        """Launch interpreter in a background thread; poll GUI with after()."""
        self._stdin_queue = queue.Queue()
        self._run_complete = False
        self._enable_stdin_input(True)
        ast = (self.last_result or {}).get("ast") or {}

        def run_worker():
            from runtime.interpreter import Interpreter
            from utils.error import CompilerError as _CE
            interp = Interpreter()

            def stdout_cb(chunk):
                self.after(0, lambda c=chunk: self._terminal_append(c, color="output"))

            def stdin_cb():
                # Block until the user types something in the entry widget
                self.after(0, lambda: self._terminal_append("\n[Waiting for input…]\n", color="prompt"))
                try:
                    line = self._stdin_queue.get(timeout=300)  # 5-min timeout
                    return line
                except queue.Empty:
                    return None

            try:
                run_result = interp.run(ast, stdin_callback=stdin_cb, stdout_callback=stdout_cb)
                rr = run_result.to_dict()
                # Update symbol table final values
                _all_vars = rr.get("all_vars") or rr.get("globals_after") or {}
                _symbols = (self.last_result.get("symbol_table") or {}).get("all_symbols") or []
                for _sym in _symbols:
                    if "(" in _sym.get("type", ""):
                        continue
                    _v = _all_vars.get(_sym["name"])
                    if _v is None:
                        _sym["final_value"] = None
                    elif isinstance(_v, list):
                        _sym["final_value"] = "{" + ", ".join(str(x) for x in _v) + "}"
                    else:
                        _sym["final_value"] = str(_v)
                self.last_result["run_result"] = rr
                rv = rr.get("return_value")
                self.after(0, lambda: self._on_run_done(rv))
            except _CE as exc:
                err_msg = _make_friendly_error(str(exc))
                self.after(0, lambda m=err_msg: self._on_run_error(m))

        self._run_thread = threading.Thread(target=run_worker, daemon=True)
        self._run_thread.start()

    def _on_run_done(self, return_value) -> None:
        self._enable_stdin_input(False)
        self._exit_code_var.set(f"exit code: {return_value}")
        self._terminal_append(f"\n[Program finished with exit code {return_value}]\n", color="info")
        self.status_var.set(f"Program finished — exit code {return_value}.")

    def _on_run_error(self, err_msg: str) -> None:
        self._enable_stdin_input(False)
        self._terminal_append(f"\n[Runtime Error]\n{err_msg}\n", color="error")
        self._exit_code_var.set("exit code: error")
        self.status_var.set("Runtime error.")
        messagebox.showerror("Runtime Error", err_msg)

    def _enable_stdin_input(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.stdin_entry.configure(state=state)
        self._stdin_send_btn.configure(state=state)

    def _on_stdin_enter(self, event=None) -> None:
        self._on_stdin_send()

    def _on_stdin_send(self) -> None:
        text = self.stdin_entry.get().strip()
        self.stdin_entry.delete(0, "end")
        self._terminal_append(f"> {text}\n", color="input")
        self._stdin_queue.put(text)

    # ── Terminal helpers ─────────────────────────────────────────────────

    def _terminal_reset(self) -> None:
        self.program_output_text.configure(state="normal")
        self.program_output_text.delete("1.0", "end")
        self.program_output_text.configure(state="disabled")
        self._exit_code_var.set("")
        self._enable_stdin_input(False)

    def _terminal_append(self, text: str, color: str = "output") -> None:
        """Append text to the terminal textbox with a colour tag."""
        COLOR_MAP = {
            "output": TEXT_CODE,
            "prompt": TEXT_GREEN,
            "input":  "#82cfff",
            "info":   TEXT_SEC,
            "error":  ACCENT_RED,
        }
        fg = COLOR_MAP.get(color, TEXT_CODE)
        tb = self.program_output_text
        tb.configure(state="normal")
        tag = f"_tag_{color}"
        try:
            tb.tag_config(tag, foreground=fg)
        except Exception:
            pass
        tb.insert("end", text, tag)
        tb.see("end")
        tb.configure(state="disabled")

    def _set_program_output(self, stdout: str, return_value) -> None:
        # Legacy shim used by older code paths
        self._terminal_reset()
        if stdout:
            self._terminal_append(stdout, color="output")
        self._exit_code_var.set(str(return_value) if return_value is not None else "")

    def _set_run_output(self, text: str) -> None:
        # Legacy shim — now we use the terminal directly; just log to status
        self.status_var.set(text[:120])

    def _set_summary(self, text: str) -> None:
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────
    # Save / folder
    # ─────────────────────────────────────────────────────────────────────

    def _save_details_report(self) -> None:
        if not self.last_result:
            messagebox.showinfo("Save report", "Compile first.")
            return
        report = format_compilation_details(self.last_result)
        output_path = filedialog.asksaveasfilename(
            title="Save compilation report",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialdir=str(OUTPUT_DIR),
            initialfile="compilation_report.txt",
        )
        if not output_path:
            return
        Path(output_path).write_text(report, encoding="utf-8")
        self.status_var.set(f"Report saved: {output_path}")

    def _open_output_folder(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(OUTPUT_DIR))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(OUTPUT_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
            self.status_var.set(f"Opened: {OUTPUT_DIR}")
        except OSError as exc:
            messagebox.showerror("Error", f"Could not open output folder:\n{exc}")

    # ─────────────────────────────────────────────────────────────────────
    # Table builders
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_lex_table_text(tokens: list[dict]) -> str:
        if not tokens:
            return "(No tokens — compile first.)"
        col_w = [6, 18, 22, 6, 8]
        header = (
            f"{'#':<{col_w[0]}}  {'Token Type':<{col_w[1]}}  {'Lexeme':<{col_w[2]}}  "
            f"{'Line':<{col_w[3]}}  {'Col':<{col_w[4]}}"
        )
        sep = "-" * (sum(col_w) + 8)
        rows = [header, sep]
        for i, t in enumerate(tokens, 1):
            lexeme = t.get("lexeme", "")
            if len(lexeme) > col_w[2]:
                lexeme = lexeme[:col_w[2]-1] + "..."
            rows.append(
                f"{str(i):<{col_w[0]}}  {t.get('type',''):<{col_w[1]}}  "
                f"{lexeme:<{col_w[2]}}  {str(t.get('line','')):<{col_w[3]}}  "
                f"{str(t.get('column','')):<{col_w[4]}}"
            )
        rows.append(sep)
        rows.append(f"Total tokens: {len(tokens)}")
        return "\n".join(rows)

    @staticmethod
    def _build_sym_table_text(result: dict) -> str:
        st = result.get("symbol_table") or {}
        symbols = st.get("all_symbols") or []
        if not symbols:
            return "(No symbols found. Compile a program with variable declarations.)"

        # Build last_value lookup from run_result — use all_vars which covers local scopes
        rr = result.get("run_result") or {}
        globals_after: dict = rr.get("all_vars") or rr.get("globals_after") or {}

        def scope_label(s):
            if s["scope_level"] == 0:
                return "global"
            if s["is_param"]:
                return "param"
            return "local"

        def init_val_str(s):
            v = s.get("init_value")
            return str(v) if v is not None else "-"

        def last_val_str(s):
            # Functions (level 0, type contains "(") have no runtime value
            if "(" in s["type"]:
                return "-"
            # Prefer final_value set after execution (covers locals and arrays)
            fv = s.get("final_value")
            if fv is not None:
                return str(fv)
            # Fallback: look up in globals_after
            v = globals_after.get(s["name"])
            if v is None:
                return "-"
            if isinstance(v, list):
                return "{" + ", ".join(str(x) for x in v) + "}"
            return str(v)

        def flag(b):
            return "yes" if b else "no"

        W_NAME  = max(max(len(s["name"]) for s in symbols), 4)
        W_TYPE  = max(max(len(s["type"]) for s in symbols), 4)
        W_SCOPE = max(max(len(scope_label(s)) for s in symbols), 5)
        W_LVL   = max(len("Level"), 5)
        W_PARAM = max(len("Param"), 5)
        W_ARR   = max(len("Array"), 5)
        W_INIT  = min(max(max(len(init_val_str(s)) for s in symbols), 10), 20)
        W_LAST  = min(max(max(len(last_val_str(s)) for s in symbols), 10), 20)
        DIV = "  |  "
        cols = [W_NAME, W_TYPE, W_SCOPE, W_LVL, W_PARAM, W_ARR, W_INIT, W_LAST]
        INNER = sum(cols) + len(DIV) * (len(cols) - 1)
        SEP = "+" + "-" * (INNER + 2) + "+"
        TITLE = "SYMBOL  TABLE"
        tp = (INNER + 2 - len(TITLE)) // 2
        title_line = "|" + " " * tp + TITLE + " " * (INNER + 2 - tp - len(TITLE)) + "|"

        def cell(text, width):
            t = str(text)
            return (t[:width-1]+"..." if len(t) > width else t).ljust(width)

        def data_row(name, typ, scope, lvl, param, arr, init, last):
            return ("| " +
                cell(name,  W_NAME)  + DIV +
                cell(typ,   W_TYPE)  + DIV +
                cell(scope, W_SCOPE) + DIV +
                cell(lvl,   W_LVL)   + DIV +
                cell(param, W_PARAM) + DIV +
                cell(arr,   W_ARR)   + DIV +
                cell(init,  W_INIT)  + DIV +
                cell(last,  W_LAST)  + " |")

        lines = [SEP, title_line, SEP,
                 data_row("Name","Type","Scope","Level","Param","Array","Init Value","Last Value"),
                 SEP]
        for s in symbols:
            lines.append(data_row(
                s["name"],
                s["type"],
                scope_label(s),
                str(s["scope_level"]),
                flag(s["is_param"]),
                flag(s["is_array"]),
                init_val_str(s),
                last_val_str(s),
            ))
        lines.extend([SEP, f"  Total symbols: {len(symbols)}"])
        return "\n".join(lines)


def main() -> None:
    app = CompilerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
