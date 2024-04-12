import ast
from textwrap import dedent

from ._ast import AstClassVisitor


def _parse(code: str, visitor: ast.NodeVisitor):
    tree = ast.parse(code)

    visitor.visit(tree)
    return visitor.finish()


def test_decorator_bare():
    clazz = _parse(
        dedent("""
    @dataclass
    class Foo:
        pass
    """),
        AstClassVisitor([]),
    )

    assert len(clazz.decorators) == 1
    assert clazz.decorators[0].name == "dataclass"
    assert clazz.decorators[0].args is None


def test_decorator_with_kwargs():
    clazz = _parse(
        dedent("""
    @dataclass(frozen=True)
    class Foo:
        pass
    """),
        AstClassVisitor([]),
    )

    assert len(clazz.decorators) == 1
    assert clazz.decorators[0].name == "dataclass"
    assert "frozen" in clazz.decorators[0].kwargs
    assert clazz.decorators[0].kwargs["frozen"] is True


def test_decorator_with_args():
    clazz = _parse(
        dedent("""
    @badonk("oh dear")
    class Foo:
        pass
    """),
        AstClassVisitor([]),
    )

    assert len(clazz.decorators) == 1
    assert clazz.decorators[0].name == "badonk"
    assert len(clazz.decorators[0].args) == 1
    assert clazz.decorators[0].args[0] == "oh dear"


def test_fields():
    clazz = _parse(
        dedent("""
    class Foo:
        cronk: int
    """),
        AstClassVisitor([]),
    )

    assert len(clazz.fields) == 1
    assert clazz.fields[0].name == "cronk"
    assert clazz.fields[0].type == "int"


def test_fields_default():
    clazz = _parse(
        dedent("""
    class Foo:
        cronk: int = 10
    """),
        AstClassVisitor([]),
    )

    assert len(clazz.fields) == 1
    assert clazz.fields[0].name == "cronk"
    assert clazz.fields[0].type == "int"
    assert clazz.fields[0].default.value == 10
