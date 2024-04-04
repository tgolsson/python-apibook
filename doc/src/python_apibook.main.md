# module `python_apibook.main`

Generates markdown from Python docstrings.

## Functions

```python
def root_module(root) -> str
```

Get the root module name from a path.

**Arguments**:
- `root(str)`: the root path

**Returns**:
- the root module name


```python
def path_to_module(root, file) -> str
```

Convert a path to a module name.

**Arguments**:
- `root(str)`: the parent directory of the file
- `file(str)`: the module name

**Returns**:
- the dotted module name


```python
def fixup_reexports(root_module, docs) -> None
```

Inlines items that are reexported from other modules via '__all__'
lists.

**Arguments**:
- `root_module(str)`
- `docs(dict[str, Module])`

```python
def run(root_dir, output_dir, summary_output_template) -> None
```

Run the docstring generator.

**Arguments**:
- `root_dir(str)`
- `output_dir(str)`
- `summary_output_template(str | None)`

## Classes

### `class Signature:`

<div style="padding-left: 20px;">

#### Fields

- `args`: `list`

- `returns`: `list`

- `docstring`: `str`

</div>

### `class Args:`

<div style="padding-left: 20px;">

Class to hold command line arguments.

#### Fields

- `root_dir`: `str`

- `output_dir`: `str`

- `summary_template_file`: `str | None` = `<ast.Constant object at 0x7fde61960730>`

#### Methods

```python
def parse() -> Args
```

Parse command line arguments.



</div>

### `class Class:`

<div style="padding-left: 20px;">

Class to hold class information.

#### Fields

- `name`: `str`

- `bases`: `list`

- `methods`: `list`

- `fields`: `list`

- `docstring`: `str`

#### Methods

```python
def to_md(self) -> None
```

Convert class to markdown.

**Arguments**:

</div>

### `class Method:`

<div style="padding-left: 20px;">

Class to hold method information.

#### Fields

- `name`: `str`

- `args`: `list`

- `kwonlyargs`: `list`

- `returns`: `str`

- `docstring`: `str`

#### Methods

```python
def to_md(self, is_method, extra_signature) -> None
```

Convert method to markdown.

**Arguments**:
- `is_method`
- `extra_signature(Signature)`

</div>

### `class Arg:`

<div style="padding-left: 20px;">

#### Fields

- `name`: `str`

- `type`: `str`

- `default`: `str | None` = `<ast.Constant object at 0x7fde61b33280>`

</div>

### `class ArgsVisitor(ast.NodeVisitor):`

<div style="padding-left: 20px;">

#### Methods

```python
def __init__(self) -> None
```

```python
def visit_arg(self, node) -> None
```

```python
def visit_(self, node) -> None
```

```python
def finish(self, default) -> None
```

</div>

### `class AstFunctionVisitor(ast.NodeVisitor):`

<div style="padding-left: 20px;">

#### Methods

```python
def __init__(self, imports) -> None
```

```python
def visit_FunctionDef(self, node) -> None
```

```python
def finish(self) -> None
```

</div>

### `class AstClassVisitor(ast.NodeVisitor):`

<div style="padding-left: 20px;">

Visitor for class declarations.

#### Methods

```python
def __init__(self, imports) -> None
```

**Arguments**:
- `imports`

```python
def visit_ClassDef(self, node) -> None
```

```python
def visit_AnnAssign(self, node) -> None
```

```python
def visit_Decorator(self, node) -> None
```

```python
def visit_FunctionDef(self, node) -> None
```

```python
def finish(self) -> None
```

</div>

### `class Module:`

<div style="padding-left: 20px;">

Class to hold module information.

#### Fields

- `name`: `str`

- `docstring`: `str`

- `classes`: `list`

- `functions`: `list`

- `variables`: `list`

- `aliases`: `list`

- `all_exports`: `list`

- `imports`: `list`

#### Methods

```python
def resolve_export(self, item) -> str
```

Resolve an export to a module + item.

**Arguments**:
- `item`

```python
def resolve_import(self, item) -> (str, str)
```

Resolve an import to a module + item.

**Arguments**:
- `item(str)`: the item to resolve

**Returns**:
- the module containing the item
the item queried


```python
def to_md(self) -> None
```

Convert module to markdown.

**Arguments**:

</div>

### `class NakedImport:`

<div style="padding-left: 20px;">

#### Fields

- `module`: `str`

#### Methods

```python
def to_md(self) -> None
```

</div>

### `class FromImport:`

<div style="padding-left: 20px;">

#### Fields

- `module`: `str`

- `names`: `list`

- `relative`: `int`

#### Methods

```python
def to_md(self) -> None
```

</div>

### `class TypeAlias:`

<div style="padding-left: 20px;">

#### Fields

- `name`: `str`

- `type`: `str`

#### Methods

```python
def to_md(self) -> None
```

</div>

### `class TypeAliasVisitor(ast.NodeVisitor):`

<div style="padding-left: 20px;">

#### Methods

```python
def __init__(self) -> None
```

```python
def visit_AnnAssign(self, node) -> None
```

```python
def finish(self) -> None
```

</div>

### `class ClassField:`

<div style="padding-left: 20px;">

#### Fields

- `name`: `str`

- `type`: `str`

- `default`: `str | None`

</div>

### `class ClassFieldVisitor(ast.NodeVisitor):`

<div style="padding-left: 20px;">

#### Methods

```python
def __init__(self) -> None
```

```python
def visit_AnnAssign(self, node) -> None
```

```python
def finish(self) -> None
```

</div>

### `class Variable:`

<div style="padding-left: 20px;">

#### Fields

- `name`: `str`

- `value`: `str`

</div>

### `class AstVisitor(ast.NodeVisitor):`

<div style="padding-left: 20px;">

#### Methods

```python
def __init__(self, module) -> None
```

```python
def visit_Assign(self, node) -> None
```

```python
def visit_AnnAssign(self, node) -> None
```

```python
def visit_Import(self, node) -> None
```

```python
def visit_ImportFrom(self, node) -> None
```

```python
def visit_ClassDef(self, node) -> None
```

```python
def visit_FunctionDef(self, node) -> None
```

```python
def visit_Module(self, node) -> None
```

```python
def finish(self) -> None
```

</div>

