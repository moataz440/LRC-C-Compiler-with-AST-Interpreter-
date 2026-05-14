from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from grammar.first_follow import EPS, compute_first, compute_follow


def _load_grammar(grammar_path: str) -> tuple[dict[str, list[list[str]]], str]:
    grammar: dict[str, list[list[str]]] = {}
    start_symbol = ""
    with open(grammar_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lhs, rhs_part = [p.strip() for p in line.split("->")]
            alts = []
            for alt in rhs_part.split("|"):
                syms = alt.strip().split()
                alts.append([] if syms == ["eps"] else syms)
            grammar.setdefault(lhs, []).extend(alts)
            if not start_symbol:
                start_symbol = lhs
    return grammar, start_symbol


# Colour palette — works in both light and dark
_PALETTE = {
    "nt_bg":      ("#1a6ead", "#2d8fd4"),
    "nt_fg":      ("#ffffff", "#ffffff"),
    "term_bg":    ("#2d7a4e", "#38a169"),
    "term_fg":    ("#ffffff", "#ffffff"),
    "eps_bg":     ("#8b5c00", "#c07a10"),
    "eps_fg":     ("#ffffff", "#ffffff"),
    "arrow":      ("#555555", "#aaaaaa"),
    "prod_bg":    ("#f0f4f8", "#1e2530"),
    "prod_border":("#ccd8e8", "#3a4555"),
    "canvas_bg":  ("#f7f9fc", "#181e27"),
    "header_bg":  ("#1a6ead", "#1a6ead"),
    "header_fg":  ("#ffffff", "#ffffff"),
    "alt_sep":    ("#aaaacc", "#556688"),
}

def _c(key: str, dark: bool) -> str:
    v = _PALETTE[key]
    return v[1] if dark else v[0]


def open_cfg_window(parent, grammar_path: str, is_dark_fn) -> None:
    grammar, start_symbol = _load_grammar(grammar_path)
    non_terminals = list(grammar.keys())
    all_syms = {s for prods in grammar.values() for prod in prods for s in prod if s != EPS}
    terminals = sorted(all_syms - set(non_terminals))
    terminal_set = set(terminals) | {"EOF"}

    first_sets = compute_first(grammar, terminal_set)
    follow_sets = compute_follow(grammar, start_symbol, terminal_set, first_sets)

    dark = is_dark_fn()

    win = ctk.CTkToplevel(parent)
    win.title("Context-Free Grammar")
    w, h = parent.winfo_screenwidth(), parent.winfo_screenheight()
    win.geometry(f"{w}x{h}+0+0")
    win.resizable(True, True)

    win.grid_rowconfigure(0, weight=0)
    win.grid_rowconfigure(1, weight=1)
    win.grid_columnconfigure(0, weight=0)
    win.grid_columnconfigure(1, weight=1)

    # ── Top bar ──────────────────────────────────────────────────────────
    topbar = ctk.CTkFrame(win, corner_radius=0, fg_color=(_c("header_bg", False), _c("header_bg", True)), height=52)
    topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
    topbar.grid_propagate(False)
    topbar.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        topbar,
        text="  Context-Free Grammar",
        font=ctk.CTkFont(size=20, weight="bold"),
        text_color="#ffffff",
    ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

    stats_text = (
        f"  {len(non_terminals)} non-terminals  ·  "
        f"{len(terminals)} terminals  ·  "
        f"{sum(len(p) for p in grammar.values())} productions  ·  "
        f"Start: {start_symbol}"
    )
    ctk.CTkLabel(
        topbar, text=stats_text,
        font=ctk.CTkFont(size=12),
        text_color="#c8e0f4",
    ).grid(row=0, column=1, padx=4, pady=10, sticky="w")

    ctk.CTkButton(
        topbar, text="✕  Close", width=110, height=34,
        command=win.destroy,
        fg_color="transparent", border_width=2,
        text_color="#ffffff", border_color="#aaccee",
    ).grid(row=0, column=2, padx=16, pady=8)

    # ── Left panel: NT list ──────────────────────────────────────────────
    left = ctk.CTkFrame(win, corner_radius=0, fg_color=(_c("prod_bg", False), _c("prod_bg", True)), width=200)
    left.grid(row=1, column=0, sticky="nsew")
    left.grid_propagate(False)
    left.grid_rowconfigure(1, weight=1)
    left.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        left, text="Non-terminals",
        font=ctk.CTkFont(size=13, weight="bold"),
    ).grid(row=0, column=0, padx=10, pady=(12, 4), sticky="w")

    nt_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
    nt_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
    nt_scroll.grid_columnconfigure(0, weight=1)

    # ── Right: tabview ───────────────────────────────────────────────────
    right = ctk.CTkFrame(win, corner_radius=0, fg_color="transparent")
    right.grid(row=1, column=1, sticky="nsew")
    right.grid_rowconfigure(0, weight=1)
    right.grid_columnconfigure(0, weight=1)

    tabs = ctk.CTkTabview(right)
    tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
    tabs.add("Productions")
    tabs.add("FIRST / FOLLOW")
    tabs.add("Visual diagram")

    # -- Productions tab --
    prod_tab = tabs.tab("Productions")
    prod_tab.grid_rowconfigure(0, weight=1)
    prod_tab.grid_columnconfigure(0, weight=1)

    prod_canvas_frame = ctk.CTkScrollableFrame(prod_tab, fg_color="transparent")
    prod_canvas_frame.grid(row=0, column=0, sticky="nsew")
    prod_canvas_frame.grid_columnconfigure(0, weight=1)

    _selected_nt = [None]

    def build_productions(filter_nt=None):
        for w in prod_canvas_frame.winfo_children():
            w.destroy()
        rule_num = 1
        for nt in non_terminals:
            if filter_nt and nt != filter_nt:
                rule_num += len(grammar[nt])
                continue
            # NT header
            hdr = ctk.CTkFrame(prod_canvas_frame, fg_color=(_c("nt_bg", False), _c("nt_bg", True)), corner_radius=8)
            hdr.grid(sticky="ew", padx=8, pady=(10, 2))
            hdr.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                hdr, text=f"  {nt}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=_c("nt_fg", dark),
                anchor="w",
            ).grid(row=0, column=0, padx=10, pady=6, sticky="w")
            if nt == start_symbol:
                ctk.CTkLabel(hdr, text="START  ", font=ctk.CTkFont(size=10),
                             text_color="#ffdd88").grid(row=0, column=1, padx=8)

            for prod in grammar[nt]:
                row_frame = ctk.CTkFrame(
                    prod_canvas_frame,
                    fg_color=(_c("prod_bg", False), _c("prod_bg", True)),
                    corner_radius=6,
                    border_width=1,
                    border_color=(_c("prod_border", False), _c("prod_border", True)),
                )
                row_frame.grid(sticky="ew", padx=16, pady=2)
                row_frame.grid_columnconfigure(1, weight=1)

                ctk.CTkLabel(
                    row_frame, text=f"({rule_num})",
                    font=ctk.CTkFont(family="Consolas", size=11),
                    text_color=("gray50", "gray55"),
                    width=38, anchor="e",
                ).grid(row=0, column=0, padx=(8, 4), pady=6)

                rhs_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                rhs_frame.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

                if not prod:
                    _make_sym_badge(rhs_frame, "ε", "eps", dark)
                else:
                    for sym in prod:
                        kind = "nt" if sym in grammar else "term"
                        _make_sym_badge(rhs_frame, sym, kind, dark)

                rule_num += 1

    def _make_sym_badge(parent, text, kind, dark):
        if kind == "nt":
            bg = (_c("nt_bg", False), _c("nt_bg", True))
            fg = _c("nt_fg", dark)
        elif kind == "eps":
            bg = (_c("eps_bg", False), _c("eps_bg", True))
            fg = _c("eps_fg", dark)
        else:
            bg = (_c("term_bg", False), _c("term_bg", True))
            fg = _c("term_fg", dark)
        badge = ctk.CTkFrame(parent, fg_color=bg, corner_radius=5)
        badge.pack(side="left", padx=3, pady=2)
        ctk.CTkLabel(
            badge, text=f" {text} ",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=fg,
        ).pack(padx=4, pady=2)

    build_productions()

    # -- FIRST / FOLLOW tab --
    ff_tab = tabs.tab("FIRST / FOLLOW")
    ff_tab.grid_rowconfigure(0, weight=1)
    ff_tab.grid_columnconfigure(0, weight=1)

    ff_scroll = ctk.CTkScrollableFrame(ff_tab, fg_color="transparent")
    ff_scroll.grid(row=0, column=0, sticky="nsew")
    ff_scroll.grid_columnconfigure(0, weight=1)
    ff_scroll.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(ff_scroll, text="FIRST sets", font=ctk.CTkFont(size=13, weight="bold")).grid(
        row=0, column=0, padx=12, pady=(10, 4), sticky="w")
    ctk.CTkLabel(ff_scroll, text="FOLLOW sets", font=ctk.CTkFont(size=13, weight="bold")).grid(
        row=0, column=1, padx=12, pady=(10, 4), sticky="w")

    for i, nt in enumerate(non_terminals, 1):
        first_members = sorted(first_sets.get(nt, set()))
        follow_members = sorted(follow_sets.get(nt, set()))

        # FIRST cell
        f_frame = ctk.CTkFrame(
            ff_scroll,
            fg_color=(_c("prod_bg", False), _c("prod_bg", True)),
            corner_radius=8,
            border_width=1,
            border_color=(_c("prod_border", False), _c("prod_border", True)),
        )
        f_frame.grid(row=i, column=0, padx=(12, 4), pady=3, sticky="ew")
        f_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_frame, text=f"FIRST({nt})",
                     font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                     anchor="w").grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")
        tokens_row = ctk.CTkFrame(f_frame, fg_color="transparent")
        tokens_row.grid(row=1, column=0, padx=8, pady=(2, 6), sticky="w")
        for sym in first_members:
            kind = "eps" if sym == EPS else ("nt" if sym in grammar else "term")
            _make_sym_badge(tokens_row, "ε" if sym == EPS else sym, kind, dark)

        # FOLLOW cell
        fw_frame = ctk.CTkFrame(
            ff_scroll,
            fg_color=(_c("prod_bg", False), _c("prod_bg", True)),
            corner_radius=8,
            border_width=1,
            border_color=(_c("prod_border", False), _c("prod_border", True)),
        )
        fw_frame.grid(row=i, column=1, padx=(4, 12), pady=3, sticky="ew")
        fw_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(fw_frame, text=f"FOLLOW({nt})",
                     font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                     anchor="w").grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")
        tokens_row2 = ctk.CTkFrame(fw_frame, fg_color="transparent")
        tokens_row2.grid(row=1, column=0, padx=8, pady=(2, 6), sticky="w")
        for sym in follow_members:
            kind = "nt" if sym in grammar else "term"
            _make_sym_badge(tokens_row2, sym, kind, dark)

    # -- Visual diagram tab --
    vis_tab = tabs.tab("Visual diagram")
    vis_tab.grid_rowconfigure(1, weight=1)
    vis_tab.grid_columnconfigure(0, weight=1)

    toolbar = ctk.CTkFrame(vis_tab, fg_color="transparent")
    toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
    ctk.CTkLabel(toolbar, text="Click a non-terminal to highlight its productions",
                 font=ctk.CTkFont(size=11), text_color=("gray40", "gray60")).pack(side="left", padx=8)
    ctk.CTkButton(toolbar, text="Reset zoom", width=100, height=28,
                  command=lambda: _reset_diagram(),
                  fg_color="transparent", border_width=1,
                  text_color=("gray20", "gray80")).pack(side="right", padx=8)

    diagram_host = ctk.CTkFrame(vis_tab, fg_color=(_c("canvas_bg", False), _c("canvas_bg", True)), corner_radius=8)
    diagram_host.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
    diagram_host.grid_rowconfigure(0, weight=1)
    diagram_host.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(
        diagram_host,
        bg=_c("canvas_bg", dark),
        highlightthickness=0,
    )
    canvas.grid(row=0, column=0, sticky="nsew")
    hbar = tk.Scrollbar(diagram_host, orient="horizontal", command=canvas.xview)
    hbar.grid(row=1, column=0, sticky="ew")
    vbar = tk.Scrollbar(diagram_host, orient="vertical", command=canvas.yview)
    vbar.grid(row=0, column=1, sticky="ns")
    canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

    _scale = [1.0]
    _drag_start = [0, 0]

    def _draw_diagram(highlight_nt=None):
        canvas.delete("all")
        # Layout: each NT gets a row, its productions fan out to the right
        NODE_W, NODE_H = 160, 36
        PROD_W, PROD_H = 120, 28
        SYM_W, SYM_H = 80, 24
        COL_GAP = 40
        ROW_GAP = 30
        LEFT_MARGIN = 20
        TOP_MARGIN = 20

        nt_color     = _c("nt_bg", dark)
        nt_text      = _c("nt_fg", dark)
        term_color   = _c("term_bg", dark)
        term_text    = _c("term_fg", dark)
        eps_color    = _c("eps_bg", dark)
        arrow_color  = _c("arrow", dark)
        highlight    = "#ff8c00"

        x_nt = LEFT_MARGIN
        y = TOP_MARGIN

        for nt in non_terminals:
            prods = grammar[nt]
            is_hl = (nt == highlight_nt)
            color = highlight if is_hl else nt_color

            # How tall is this NT block?
            block_h = max(NODE_H, len(prods) * (PROD_H + 8) - 8)
            nt_mid_y = y + block_h // 2

            # Draw NT box
            x0, y0 = x_nt, nt_mid_y - NODE_H // 2
            x1, y1 = x0 + NODE_W, y0 + NODE_H
            r = 8
            canvas.create_rectangle(x0+r, y0, x1-r, y1, fill=color, outline="", tags=("nt", nt))
            canvas.create_rectangle(x0, y0+r, x1, y1-r, fill=color, outline="", tags=("nt", nt))
            canvas.create_oval(x0, y0, x0+2*r, y0+2*r, fill=color, outline="", tags=("nt", nt))
            canvas.create_oval(x1-2*r, y0, x1, y0+2*r, fill=color, outline="", tags=("nt", nt))
            canvas.create_oval(x0, y1-2*r, x0+2*r, y1, fill=color, outline="", tags=("nt", nt))
            canvas.create_oval(x1-2*r, y1-2*r, x1, y1, fill=color, outline="", tags=("nt", nt))
            canvas.create_text((x0+x1)//2, (y0+y1)//2, text=nt,
                               fill=nt_text, font=("Consolas", 11, "bold"), tags=("nt", nt))

            if nt == start_symbol:
                canvas.create_text(x0 + NODE_W + 6, nt_mid_y, text="★",
                                   fill="#ffcc00", font=("Consolas", 12), anchor="w")

            # Connector from right edge of NT to productions column
            x_prods = x_nt + NODE_W + COL_GAP
            canvas.create_line(x1, nt_mid_y, x_prods, nt_mid_y,
                                fill=arrow_color, width=1, dash=(4, 3))

            # Draw each production
            prod_start_y = y
            for prod in prods:
                prod_mid_y = prod_start_y + PROD_H // 2

                # Arrow from NT connector to this prod row
                canvas.create_line(x_prods, nt_mid_y, x_prods, prod_mid_y,
                                   fill=arrow_color, width=1)
                # Arrow tip
                canvas.create_line(x_prods, prod_mid_y, x_prods + 8, prod_mid_y,
                                   fill=arrow_color, width=1,
                                   arrow=tk.LAST, arrowshape=(8, 10, 4))

                x_sym = x_prods + 14
                if not prod:
                    # ε production
                    _draw_sym_box(canvas, x_sym, prod_mid_y - SYM_H//2, SYM_W, SYM_H,
                                  "ε", eps_color, "#ffffff")
                else:
                    for sym in prod:
                        is_nt_sym = sym in grammar
                        bg = nt_color if is_nt_sym else term_color
                        fg = nt_text if is_nt_sym else term_text
                        _draw_sym_box(canvas, x_sym, prod_mid_y - SYM_H//2, SYM_W, SYM_H,
                                      sym, bg, fg)
                        x_sym += SYM_W + 6

                prod_start_y += PROD_H + 8

            y += block_h + ROW_GAP

        canvas.configure(scrollregion=canvas.bbox("all"))

    def _draw_sym_box(cv, x, y, w, h, text, bg, fg):
        r = 5
        cv.create_rectangle(x+r, y, x+w-r, y+h, fill=bg, outline="")
        cv.create_rectangle(x, y+r, x+w, y+h-r, fill=bg, outline="")
        cv.create_oval(x, y, x+2*r, y+2*r, fill=bg, outline="")
        cv.create_oval(x+w-2*r, y, x+w, y+2*r, fill=bg, outline="")
        cv.create_oval(x, y+h-2*r, x+2*r, y+h, fill=bg, outline="")
        cv.create_oval(x+w-2*r, y+h-2*r, x+w, y+h, fill=bg, outline="")
        label = text if len(text) <= 10 else text[:9] + "…"
        cv.create_text(x + w//2, y + h//2, text=label,
                       fill=fg, font=("Consolas", 10, "bold"))

    def _on_nt_click(event):
        items = canvas.find_withtag("current")
        if not items:
            return
        tags = canvas.gettags(items[0])
        for tag in tags:
            if tag in non_terminals:
                _draw_diagram(highlight_nt=tag)
                _selected_nt[0] = tag
                build_productions(filter_nt=tag)
                tabs.set("Productions")
                return

    def _reset_diagram():
        _selected_nt[0] = None
        _draw_diagram()
        build_productions()

    canvas.tag_bind("nt", "<Button-1>", _on_nt_click)

    # Mouse wheel scroll
    def _on_wheel(event):
        if event.state & 0x4:
            canvas.xview_scroll(int(-event.delta / 60), "units")
        else:
            canvas.yview_scroll(int(-event.delta / 120), "units")
    canvas.bind("<MouseWheel>", _on_wheel)
    canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    _draw_diagram()

    # ── Left NT list buttons ─────────────────────────────────────────────
    ctk.CTkButton(
        nt_scroll, text="All", height=28, anchor="w",
        fg_color="transparent", text_color=("gray20", "gray80"),
        command=lambda: (_reset_diagram(), tabs.set("Productions")),
    ).grid(sticky="ew", padx=4, pady=(0, 6))

    for nt in non_terminals:
        nt_local = nt
        ctk.CTkButton(
            nt_scroll,
            text=f"  {nt_local}",
            height=28,
            anchor="w",
            fg_color=(
                (_c("nt_bg", False), _c("nt_bg", True))
                if nt_local == start_symbol
                else "transparent"
            ),
            text_color=(
                (_c("nt_fg", dark), _c("nt_fg", dark))
                if nt_local == start_symbol
                else ("gray20", "gray80")
            ),
            font=ctk.CTkFont(family="Consolas", size=12),
            command=lambda n=nt_local: (
                _draw_diagram(highlight_nt=n),
                build_productions(filter_nt=n),
                tabs.set("Productions"),
            ),
        ).grid(sticky="ew", padx=4, pady=1)

    win.lift()
    win.focus_force()
