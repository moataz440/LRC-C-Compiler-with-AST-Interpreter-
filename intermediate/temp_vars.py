from __future__ import annotations


class TempFactory:
    """
    Generates unique names for compiler temporaries and control-flow labels.

    Temporaries are named  _t1, _t2, ...  (the leading underscore makes it
    obvious they are synthetic and avoids collisions with user variables).

    Labels are named  <prefix>_1, <prefix>_2, ...  which keeps the TAC
    output readable even after many optimisation passes.
    """

    def __init__(self) -> None:
        self._temp_count = 0
        self._label_count = 0

    def new_temp(self) -> str:
        self._temp_count += 1
        return f"_t{self._temp_count}"

    def new_label(self, prefix: str = "L") -> str:
        self._label_count += 1
        return f"{prefix}{self._label_count}"
