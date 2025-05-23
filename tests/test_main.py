from pathlib import Path

import pytest
from tomlkit import array

from uv_sort.main import sort_array_by_name, sort_toml_project


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('["foo", "bar"]', '["bar", "foo"]'),
        # should be multi-line if there is a line-break
        ('["foo", \n"bar"]', '[ \n"bar","foo",\n]'),
        # should be multi-line if there is a comment
        ('["foo", # baz \n"bar"]', '[\n"bar","foo", # baz \n]'),
        # should be intact if it only has one element
        ('["foo" # bar\n]', '["foo" # bar\n]'),
        # ref. https://github.com/ninoseki/uv-sort/issues/18
        (
            '["dvc-pandas>=0.3.3", "dvc[azure]>=3.59.2", "uv-sort>=0.5.1"]',
            '["dvc-pandas>=0.3.3", "dvc[azure]>=3.59.2", "uv-sort>=0.5.1"]',
        ),
    ],
)
def test_sort_array_by_name(raw: str, expected: str):
    arr = array(raw)
    _sorted = sort_array_by_name(arr)
    assert _sorted.as_string() == expected


@pytest.fixture
def plain() -> str:
    return Path("tests/fixtures/plain/pyproject.toml").read_text()


def test_with_plain(plain: str):
    _sorted = sort_toml_project(plain)

    sorted_dependencies = sorted(["foo", "bar"])

    # array
    assert _sorted["project"]["dependencies"] == sorted_dependencies  # type: ignore
    assert _sorted["tool"]["uv"]["dev-dependencies"] == sorted_dependencies  # type: ignore
    # table
    assert _sorted["project"]["optional-dependencies"] == {"docs": sorted_dependencies}  # type: ignore
    assert _sorted["dependency-groups"] == {"dev": sorted_dependencies}  # type: ignore
    assert _sorted["tool"]["uv"]["sources"] == {  # type: ignore
        "bar": {"git": "https://github.com/ninoseki/bar"},
        "foo": {"git": "https://github.com/ninoseki/foo"},
    }


@pytest.fixture
def comment() -> str:
    return Path("tests/fixtures/with-comment/pyproject.toml").read_text()


def test_with_comment(comment: str):
    _sorted = sort_toml_project(comment)

    sorted_dependencies = sorted(["foo", "bar"])

    assert _sorted["project"]["dependencies"] == sorted_dependencies  # type: ignore
    assert (
        _sorted["project"]["dependencies"].as_string()  # type: ignore
        == '[\n  "bar", # baz\n  "foo",\n]'
    )

    assert _sorted["tool"]["uv"]["dev-dependencies"] == sorted_dependencies  # type: ignore
    assert (
        _sorted["tool"]["uv"]["dev-dependencies"].as_string()  # type: ignore
        == '[\n  "bar", # baz\n  "foo",\n]'
    )

    assert _sorted["project"]["optional-dependencies"] == {"docs": sorted_dependencies}  # type: ignore
    assert (
        _sorted["project"]["optional-dependencies"].as_string()  # type: ignore
        == 'docs = [\n  "bar", # baz\n  "foo",\n]\n\n'
    )

    assert _sorted["dependency-groups"] == {"dev": sorted_dependencies}  # type: ignore
    assert (
        _sorted["dependency-groups"].as_string()  # type: ignore
        == '# baz\ndev = [\n  "bar", # baz\n  "foo",\n]\n'
    )

    assert _sorted["tool"]["uv"]["sources"] == {  # type: ignore
        "bar": {"git": "https://github.com/ninoseki/bar"},
        "foo": {"git": "https://github.com/ninoseki/foo"},
    }
    assert (
        _sorted["tool"]["uv"]["sources"].as_string()  # type: ignore
        == 'bar = { git = "https://github.com/ninoseki/bar" }\nfoo = { git = "https://github.com/ninoseki/foo" }\n\n'
    )
