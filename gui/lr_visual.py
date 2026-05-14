"""LR parser trace as a color-coded, scrollable text 'visual' table."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any


def render_lr_trace(
    parent: tk.Misc,
    trace: list[dict[str, Any]],
    is_dark: Callable[[], bool] | None = None,
) -> tk.Text:
    frame = tk.Frame(parent)
    frame.pack(fill="both", expand=True)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    yscroll = tk.Scrollbar(frame, orient="vertical")
    text = tk.Text(
        frame,
        font=("Consolas", 9),
        wrap="none",
        height=20,
        yscrollcommand=yscroll.set,
        state="normal",
    )
    hscroll = tk.Scrollbar(frame, orient="horizontal", command=text.xview)
    text.config(xscrollcommand=hscroll.set)
    text.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    hscroll.grid(row=1, column=0, sticky="ew")
    yscroll.config(command=text.yview)

    def th() -> str:
        return "dark" if (is_dark and is_dark()) else "light"

    def refresh() -> None:
        t = th()
        text.config(state="normal")
        text.delete("1.0", "end")
        for tag in ("h", "alt1", "alt2", "sep"):
            try:
                text.tag_delete(tag)
            except tk.TclError:
                pass
        if t == "dark":
            text.config(bg="#0F1117", fg="#E2E8F0", insertbackground="#E2E8F0")
            text.tag_configure("h", background="#1E3A5F", foreground="#E2E8F0", font=("Consolas", 9, "bold"))
            text.tag_configure("alt1", background="#111827", foreground="#E2E8F0")
            text.tag_configure("alt2", background="#0B1220", foreground="#D1D5DB")
        else:
            text.config(bg="#FAFBFF", fg="#0F172A", insertbackground="#0F172A")
            text.tag_configure("h", background="#C7D2FE", foreground="#0F172A", font=("Consolas", 9, "bold"))
            text.tag_configure("alt1", background="#F8FAFC", foreground="#0F172A")
            text.tag_configure("alt2", background="#EEF2FF", foreground="#1E293B")

        if not trace:
            text.insert("1.0", "No LR trace (empty or compile failed).")
            text.config(state="disabled")
            return

        header = f"{'Step':>4}  {'State stack (bottom→top)':<52}  {'Lookahead':<20}  Action\n"
        text.insert("end", header, "h")
        text.insert("end", "-" * 110 + "\n", "h")

        for i, row in enumerate(trace):
            tag = "alt1" if i % 2 == 0 else "alt2"
            la = row.get("lookahead") or {}
            st = row.get("state_stack", [])
            try:
                st_s = str(st)
            except Exception:
                st_s = "?"
            if len(st_s) > 50:
                st_s = st_s[:47] + "…"
            look = f"{la.get('lexeme', '')!r} ({la.get('type', '')})"
            if len(look) > 22:
                look = look[:20] + "…"
            line = f"{row.get('step', i):4}  {st_s:<52}  {look:<20}  {row.get('action', '')}\n"
            text.insert("end", line, tag)
        text.config(state="disabled")

    text._lr_refresh = refresh  # type: ignore[attr-defined]
    refresh()
    return text
