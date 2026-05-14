from __future__ import annotations


def asm_to_hte(asm_lines: list[str], *, program_name: str = "PROG", start_addr: int = 0) -> str:
    name = (program_name[:6].upper() if program_name else "PROG").ljust(6, "_")
    blob = _encode_program(asm_lines)
    length = len(blob)

    records: list[str] = []
    records.append(f"H^{name}^{start_addr:06X}^{length:06X}")

    addr = start_addr
    i = 0
    max_chunk = 30
    while i < len(blob):
        chunk = blob[i : i + max_chunk]
        records.append(f"T^{addr:06X}^{len(chunk):02X}^{chunk.hex().upper()}")
        addr += len(chunk)
        i += len(chunk)

    records.append(f"E^{start_addr:06X}")
    return "\n".join(records) + "\n"


def _encode_program(lines: list[str]) -> bytes:
    # Keep each instruction on its own line for readability in hex-to-text debugging.
    text = "\n".join(lines).strip() + "\n"
    return text.encode("utf-8", errors="replace")

