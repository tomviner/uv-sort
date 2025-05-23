from pathlib import Path
from typing import Optional, cast

import tomlkit
from tomlkit.container import Container
from tomlkit.items import (
    Array,
    Comment,
    Null,
    Table,
    Whitespace,
    _ArrayItemGroup,
)


def is_processable(item: _ArrayItemGroup) -> bool:
    if not item.value:
        return False

    return not isinstance(item.value, (Comment, Whitespace, Null))


def key_builder(item: _ArrayItemGroup) -> str:
    return str(item.value).casefold()


def one_line_array_mapper(
    item: _ArrayItemGroup,
    *,
    first: bool = False,
    last: bool = False,
    indent: str = "",
) -> str:
    if item.value is None:
        return ""

    return "".join(
        [
            indent,
            "" if first else " ",
            item.value.as_string(),
            "" if last else ",",
            item.comment.as_string() if item.comment else "",
        ]
    )


def multi_line_array_mapper(item: _ArrayItemGroup, *, indent: str, **kwargs) -> str:
    if item.value is None:
        return ""

    # always add a comma at the end of the line
    comma = item.comma.as_string() if item.comma else ""
    if not comma.strip().endswith(","):
        comma = comma.strip() + ","

    return "".join(
        [
            indent,
            item.indent.as_string() if item.indent else "",
            item.value.as_string(),
            comma,
            item.comment.as_string() if item.comment else "",
        ]
    )


def sort_array_by_name(x: Array) -> Array:
    if len(x) <= 1:
        # nothing to sort
        return x

    # reject ArrayItemGroup doesn't have a value (e.g. trailing ",", comment)
    filtered: list[_ArrayItemGroup] = [
        item for item in x._value if is_processable(item)
    ]
    # sort the array
    _sorted = sorted(filtered, key=key_builder)
    # rebuild the array with preserving comments & indentation
    # consider adding a line-break at last if the last indent has a line-break
    last_indent = _sorted[-1].indent
    has_line_break_at_last = (
        last_indent.as_string() if last_indent else ""
    ).startswith("\n")
    is_multiline = x.as_string().count("\n") > 0
    #  add line-break at last if the last indent has a line-break or it's multiline array
    last_line_break = "\n" if has_line_break_at_last or is_multiline else ""

    mapper = multi_line_array_mapper if is_multiline else one_line_array_mapper
    mapped: list[str] = [
        mapper(
            item,
            first=index == 0,
            last=index == len(_sorted) - 1,
            indent=x.trivia.indent,
        )
        for index, item in enumerate(_sorted)
    ]

    s = "[" + "".join(mapped) + x.trivia.indent + last_line_break + "]"
    return tomlkit.array(s).multiline(x._multiline)


def sort_table_by_name(x: Table) -> Table:
    _sorted = Table(
        Container(),
        trivia=x.trivia,
        is_aot_element=x.is_aot_element(),
        is_super_table=x.is_super_table(),
        name=x.name,
        display_name=x.display_name,
    )

    for k, v in x.value.body:
        if k is None:
            # NOTE: v = Comment or Whitespace, etc?
            #       anyway it should not be Array for sure
            _sorted.add(v)  # type: ignore
            continue

        v = cast(Array, v)
        _sorted.append(k, sort_array_by_name(v))

    return _sorted


def sort_sources(x: Table) -> Table:
    _sorted = Table(
        Container(),
        trivia=x.trivia,
        is_aot_element=x.is_aot_element(),
        is_super_table=x.is_super_table(),
        name=x.name,
        display_name=x.display_name,
    )
    _sorted.update(sorted(x.items()))
    return _sorted


def sort_toml_project(text: str) -> tomlkit.TOMLDocument:
    parsed = tomlkit.parse(text)

    # sort project.dependencies (array)
    dependencies: Optional[Array] = parsed.get("project", {}).get("dependencies")
    if dependencies:
        parsed["project"]["dependencies"] = sort_array_by_name(dependencies)  # type: ignore

    # sort project.dev-dependencies (array)
    dev_dependencies: Optional[Array] = (
        parsed.get("tool", {}).get("uv", {}).get("dev-dependencies")
    )
    if dev_dependencies:
        parsed["tool"]["uv"]["dev-dependencies"] = sort_array_by_name(dev_dependencies)  # type: ignore

    # sort project.optional-dependencies (table)
    optional_dependencies: Optional[Table] = parsed.get("project", {}).get(
        "optional-dependencies"
    )
    if optional_dependencies:
        parsed["project"]["optional-dependencies"] = sort_table_by_name(  # type: ignore
            optional_dependencies
        )

    # sort dependency-groups (table)
    dependency_groups: Optional[Table] = parsed.get("dependency-groups")
    if dependency_groups:
        parsed["dependency-groups"] = sort_table_by_name(dependency_groups)

    # sort tool.uv.sources (table)
    sources: Optional[Table] = parsed.get("tool", {}).get("uv", {}).get("sources")
    if sources:
        parsed["tool"]["uv"]["sources"] = sort_sources(sources)  # type: ignore

    return parsed


def sort(path: Path) -> str:
    _sorted = sort_toml_project(path.read_text())
    return tomlkit.dumps(_sorted)
