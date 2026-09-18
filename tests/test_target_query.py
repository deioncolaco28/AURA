"""Tests for TargetQuery data model and parse_ordinal helper."""

import pytest

from app.perception.target_query import (
    ORDINAL_FIRST,
    ORDINAL_LAST,
    ORDINAL_SECOND_LAST,
    RELATION_ABOVE,
    RELATION_BELOW,
    RELATION_LEFT,
    RELATION_NEAREST,
    RELATION_RIGHT,
    TargetQuery,
    parse_ordinal,
)


# ---------------------------------------------------------------------------
# parse_ordinal
# ---------------------------------------------------------------------------


class TestParseOrdinal:

    def test_first(self):
        assert parse_ordinal("first") == 1

    def test_second(self):
        assert parse_ordinal("second") == 2

    def test_third(self):
        assert parse_ordinal("third") == 3

    def test_last(self):
        assert parse_ordinal("last") == ORDINAL_LAST

    def test_second_last_hyphen(self):
        assert parse_ordinal("second-last") == ORDINAL_SECOND_LAST

    def test_second_last_space(self):
        assert parse_ordinal("second last") == ORDINAL_SECOND_LAST

    def test_numeric_ordinal_2nd(self):
        assert parse_ordinal("2nd") == 2

    def test_numeric_ordinal_3rd(self):
        assert parse_ordinal("3rd") == 3

    def test_numeric_ordinal_4th(self):
        assert parse_ordinal("4th") == 4

    def test_plain_integer(self):
        assert parse_ordinal("5") == 5

    def test_unknown_returns_none(self):
        assert parse_ordinal("penultimate") is None

    def test_empty_returns_none(self):
        assert parse_ordinal("") is None

    def test_case_insensitive(self):
        assert parse_ordinal("FIRST") == 1
        assert parse_ordinal("Last") == ORDINAL_LAST


# ---------------------------------------------------------------------------
# TargetQuery construction
# ---------------------------------------------------------------------------


class TestTargetQueryConstruction:

    def test_simple_text(self):
        q = TargetQuery(text="Notepad")
        assert q.text == "Notepad"
        assert q.is_simple_text
        assert not q.has_ordinal
        assert not q.has_relation

    def test_ordinal_first(self):
        q = TargetQuery(ordinal=1)
        assert q.has_ordinal
        assert not q.is_reverse_ordinal

    def test_ordinal_last(self):
        q = TargetQuery(ordinal=ORDINAL_LAST)
        assert q.has_ordinal
        assert q.is_reverse_ordinal

    def test_ordinal_second_last(self):
        q = TargetQuery(ordinal=ORDINAL_SECOND_LAST)
        assert q.has_ordinal
        assert q.is_reverse_ordinal

    def test_relational_requires_both(self):
        q = TargetQuery(relation=RELATION_BELOW, reference="Calculator")
        assert q.has_relation

    def test_relation_without_reference_not_relational(self):
        q = TargetQuery(relation=RELATION_BELOW)
        assert not q.has_relation  # reference is None → not relational

    def test_group_with_ordinal(self):
        q = TargetQuery(group="search_result", ordinal=2)
        assert q.has_ordinal
        assert q.group == "search_result"

    def test_element_type(self):
        q = TargetQuery(element_type="button", relation=RELATION_RIGHT, reference="Search")
        assert q.has_relation
        assert q.element_type == "button"


# ---------------------------------------------------------------------------
# TargetQuery.describe()
# ---------------------------------------------------------------------------


class TestTargetQueryDescribe:

    def test_simple_text_describe(self):
        q = TargetQuery(text="Notepad")
        assert "Notepad" in q.describe()

    def test_ordinal_describe(self):
        q = TargetQuery(ordinal=2, group="option")
        desc = q.describe()
        assert "second" in desc
        assert "option" in desc

    def test_last_describe(self):
        q = TargetQuery(ordinal=ORDINAL_LAST)
        assert "last" in q.describe()

    def test_relational_describe(self):
        q = TargetQuery(relation=RELATION_BELOW, reference="Calculator")
        desc = q.describe()
        assert "below" in desc
        assert "Calculator" in desc

    def test_empty_describe(self):
        q = TargetQuery()
        assert q.describe() == "unspecified target"
