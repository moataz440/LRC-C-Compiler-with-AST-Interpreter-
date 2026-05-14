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

## Input Files

The `tests/` folder contains sample C++ programs you can load directly into the GUI or pass to `main.py`:

```
tests/
├── sample.cpp           full example using arrays, if, for, and functions
├── test.cpp             increment/decrement edge cases
├── test1.txt            basic arithmetic and variable declarations
├── test2.txt            nested expressions
├── test_cpp.txt         mixed types and operators
└── test_for_loop.txt    for loop with array traversal
```

Example from `sample.cpp`:

```cpp
#include <iostream>
using namespace std;

int main() {
    int a = 1;
    double b = 2.5;
    bool ok = true;
    int arr[] = {1, 2, 3};

    if (ok && a < 10) {
        a = a + arr[0];
    }

    for (int i = 0; i < 3; i = i + 1) {
        b = b + 0.1;
    }

    return a;
}
```

---

## Output Files

The compiler output is not just the program result. Every time you compile, the full output of each phase is automatically saved inside the `output/` folder. You can open any of them in a text editor or JSON viewer without using the GUI.

```
output/
│
├── tokens.json          # every token the lexer produced
│                        # includes type, lexeme, line, and column
│                        # example: {"type":"TYPE","lexeme":"int","line":3,"column":1}
│
├── preprocessor.json    # all directives found by the preprocessor
│                        # includes #include and #define records
│
├── ast.json             # the full Abstract Syntax Tree
│                        # the JSON tree the interpreter runs on
│
├── parse_tree.json      # full parse tree from the LR(1) parser
│                        # every grammar rule applied during parsing
│
├── lr_trace.json        # step-by-step LR(1) parser trace
│                        # shows every shift, reduce, and goto action
│
├── symbol_table.json    # every declared variable
│                        # includes name, type, scope, and initial value
│
├── tac.txt              # Three-Address Code — the intermediate representation
│                        # example:
│                        #   _t1 = i < 2
│                        #   ifFalse _t1 goto FOR_END
│                        #   _t2 = x[i]
│                        #   sum = sum + _t2
│
├── program.asm          # pseudo-assembly generated from TAC
│                        # example:
│                        #   LT  _t1, i, 2
│                        #   IF_FALSE _t1, GOTO FOR_END
│                        #   MOV _t2, x[i]
│                        #   ADD sum, sum, _t2
│
├── program.obj          # HTE-format object code (Header / Text / End)
│                        # the final output of the assembler phase
│
└── run_result.json      # the program's actual output and return value
                         # example: {"stdout": "4", "return_value": 0}
```

---

## Error Handling

The compiler reports errors at each phase with precise location and actionable hints — it does not just say something went wrong.

**Syntax errors** include the exact line and column, the unexpected token, what was expected instead, and a suggested fix:

```
Syntax error at '}' (RBRACE) on line 8, column 1.
Expected: ';'
Possible fixes:
  - You may be missing a ';' before this token.
  - If the previous statement is missing ';', add it before '}'.
```

**Semantic errors** catch type mismatches, undeclared variables, missing headers, and invalid array declarations before execution:

```
Semantic error: 'cout' requires '#include <iostream>' but it was not found.
Semantic error: cannot assign floating-point expression to int variable 'x' without a cast.
Semantic error: array 'arr' declared without a size or initializer list.
Semantic error: variable 'y' used before declaration.
```

**Runtime errors** catch division by zero, out-of-bounds array access, and missing input during execution:

```
Runtime error: division by zero.
Runtime error: array index 5 out of range (size 3).
Runtime error: cin reached end of provided input.
```

All errors are displayed in the GUI output panel with the phase that caught them clearly labeled.

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

## Tech Stack

`Python 3` · `CustomTkinter` · `LR(1) Parsing` · `AST Interpretation`

---

## License

MIT License — see `LICENSE` for details.
