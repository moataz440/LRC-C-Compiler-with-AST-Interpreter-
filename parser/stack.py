
class Stack:
    def __init__(self) -> None:
        self._data: list = []

    def push(self, value) -> None:
        self._data.append(value)

    def pop(self):
        return self._data.pop()

    def peek(self):
        return self._data[-1]

    def __len__(self) -> int:
        return len(self._data)

    def as_list(self) -> list:
        """Return a shallow copy of stack contents (bottom to top)."""
        return list(self._data)
