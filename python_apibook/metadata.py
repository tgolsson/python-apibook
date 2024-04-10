import logging
from dataclasses import dataclass, field
from enum import Enum

from docstring_parser import parse

logger = logging.getLogger(__name__)


class FieldKind(Enum):
    """Enum to hold information about the kind of a field in a class."""

    INSTANCE = "instance"
    """Instance variable."""

    CLASS = "class"
    """Class variable."""

    MODULE = "module"
    """Module variable."""

    UNKNOWN = "unknown"
    """Unknown or unspecified location for variable."""

    def from_str(kind: str) -> "FieldKind":
        """Convert from a str to enum variant."""
        if kind == "ivar":
            return FieldKind.INSTANCE
        elif kind == "cvar":
            return FieldKind.CLASS
        elif kind == "var":
            return FieldKind.MODULE
        else:
            logger.warning(f"Unknown field kind: {kind!r}")
            return FieldKind.UNKNOWN


@dataclass
class Field:
    """Information about a single field in a class."""

    name: str
    type: str
    description: str

    kind: FieldKind = FieldKind.UNKNOWN


@dataclass
class ClassDetail:
    """Holds infomation about a class combined from multiple sources."""

    fields: list[Field] = field(default_factory=list)

    def by_name(self, name: str) -> Field | None:
        for field in self.fields:
            if field.name == name:
                return field

        return None

    def with_docstring_source(self, docstring: str):
        metadata = parse(docstring)

        for meta_item in metadata.meta:
            logger.debug(f"Processing item {vars(meta_item)}")
            match meta_item.args[0]:
                case "attribute":
                    field = Field(
                        meta_item.arg_name,
                        meta_item.type_name,
                        meta_item.description,
                    )
                    self.fields.append(field)

                case "type":  # epydoc
                    if field := self.by_name(meta_item.arg_name):
                        field.type = meta_item.type_name

                case "ivar" | "cvar" | "var":  # epydoc
                    if field := self.by_name(meta_item.args[1]):
                        field.docstring = meta_item.description
                    else:
                        field = Field(
                            meta_item.args[1],
                            meta_item.args[2] if len(meta_item.args) > 2 else None,
                            meta_item.description,
                            FieldKind.from_str(meta_item.args[0]),
                        )

                        self.fields.append(field)

        return self


@dataclass
class Signature:
    """Class to hold signature information for a function or method.

    Might also be used to hold information about a class constructor,
    even if those are defined on the class itself.
    """

    args: list
    returns: list
    docstring: str
