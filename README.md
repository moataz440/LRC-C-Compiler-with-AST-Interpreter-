# LRC — C++ Frontend Compiler with AST Interpreter

An educational C++ compiler built in Python that walks through all major compilation phases, visualized through a modern CustomTkinter GUI.

---

## How It Works

You write C++. The compiler processes it through a full pipeline and executes it using a built-in AST interpreter — no linker or loader required, because execution never touches the generated object code. Python itself acts as the runtime engine.

```
Source Code
    │
    ├─► Preprocessor      →  strips #include / #define
    ├─► Lexer             →  tokens
    ├─► LR(1) Parser      →  Abstract Syntax Tree (AST)
    ├─► Semantic Analyzer →  type checking + symbol table
    ├─► TAC Generator     →  three-address code
    ├─► ASM Generator     →  pseudo-assembly
    ├─► Assembler         →  HTE object code  (display only)
    │
    └─► AST Interpreter   →  executes the program, produces output
```

---

## Project Structure

```
project/
├── preprocessor/       #include / #define handling
├── lexer/              tokenizer and token rules
├── grammar/            LR(1) table builder and grammar definition
├── parser/             LR(1) parser and AST builder
├── semantic/           type checker and symbol table
├── intermediate/       TAC generator and optimizer
├── codegen/            pseudo-assembly generator
├── assembler/          HTE object code encoder
├── runtime/            AST tree-walking interpreter
├── gui/                GUI tree canvas and visual components
├── utils/              error handling and helpers
├── tests/              sample C++ programs
├── output/             generated files (tokens, AST, TAC, ASM, OBJ)
├── gui.py              main GUI entry point
└── main.py             compiler pipeline
```

---

## Supported C++ Features

- Primitive types: `int`, `float`, `double`, `bool`, `char`, `string`
- Arrays with size or initializer list: `int arr[3]` / `int arr[] = {1, 2, 3}`
- Arithmetic, relational, and logical operators
- Pre/post increment and decrement: `++x`, `x--`
- `if` / `else` statements
- `for` loops
- Functions with parameters and return values
- `cout` and `cin`
- `#include <iostream>` and `using namespace std;`

---

## GUI Tabs

| Tab | Shows |
|---|---|
| Lexical Table | Every token with type, lexeme, line, and column |
| AST | Abstract Syntax Tree as an interactive diagram |
| Parse Tree | Full parse tree from the LR(1) parser |
| LR Parser | Step-by-step LR(1) trace |
| Intermediate Code | Three-Address Code (TAC) |
| Object Code | HTE-format pseudo object code |
| Symbol Table | All variables with name, type, scope, and value |

---

## Getting Started

**Requirements:** Python 3.10+

**Install dependencies:**
```bash
pip install customtkinter
```

**Run the GUI:**
```bash
python gui.py
```

**Run the compiler pipeline directly:**
```bash
python main.py
```

---

## Example

```cpp
#include <iostream>
using namespace std;

int main() {
    int x = 5;
    int y = 3;
    cout << x + y;
    return 0;
}
```

Output:
```
8
```

---

## Tech Stack

`Python 3` · `CustomTkinter` · `LR(1) Parsing` · `AST Interpretation`

---

## License

MIT License — see `LICENSE` for details.
