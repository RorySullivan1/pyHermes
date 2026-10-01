"""
The glossary (#311): terms defined once, which the body links to by an ordinary anchor.
"""

from __future__ import annotations

import re

import pytest

from pyhermes.builder import FullWidth, Glossary, Term, TextBlock, ValidationError
from pyhermes.builder.email import Email
from pyhermes.check.lint import Severity, lint_document
from pyhermes.document import PagedDocument

FACTS = {"email_subject": "Subject", "firm_name": "Hermes", "campaign_name": "Review"}

TERMS = [
    Term("Duration", "The sensitivity of a bond's price to a change in its yield."),
    Term("Carry", "What a position earns if prices do not move."),
    Term("Z-spread", "The spread over the zero curve that prices a bond at its market price."),
]


def document(link: str = "#term-duration", built=None):
    built = built if built is not None else Email(FACTS)
    built.add_section(
        FullWidth(
            title="Body", content=TextBlock(f'<p>Its <a href="{link}">duration</a> fell.</p>')
        )
    )
    built.add_section(FullWidth(title="Glossary", content=Glossary(TERMS)))
    return built


class TestTheLinks:
    def test_a_link_to_a_term_validates_and_lands(self):
        built = document()
        built.validate()
        assert '<p id="term-duration"' in built.render()

    def test_a_link_to_a_missing_term_is_named(self):
        with pytest.raises(ValidationError, match="#term-missing"):
            document("#term-missing").validate()

    def test_every_term_is_anchored_by_its_slug(self):
        assert [t.anchor() for t in TERMS] == ["term-duration", "term-carry", "term-z-spread"]

    def test_the_text_prints_a_term_link_as_its_label(self):
        assert "Its duration fell." in document().text()


class TestTheLayout:
    def test_terms_sort_unless_asked_not_to(self):
        assert [t.term for t in Glossary(TERMS).terms] == ["Carry", "Duration", "Z-spread"]
        assert [t.term for t in Glossary(TERMS, sort=False).terms] == [
            "Duration",
            "Carry",
            "Z-spread",
        ]

    def test_the_text_is_one_term_per_paragraph(self):
        assert Glossary(TERMS[:2], title="Terms").text() == (
            "Terms\n-----\n\n"
            "Carry: What a position earns if prices do not move.\n\n"
            "Duration: The sensitivity of a bond's price to a change in its yield."
        )

    def test_both_cells_stack_on_a_phone(self):
        html = document().render()
        row = re.search(r'<table class="glossary".*?</tr>', html, re.S).group(0)
        assert row.count('class="stack-column"') == 2

    @pytest.mark.parametrize("medium", ["email", "paper"])
    def test_it_is_lint_clean(self, medium):
        paper = PagedDocument({"firm_name": "Hermes", "campaign_name": "Review"})
        built = document(built=None if medium == "email" else paper)
        assert not [f for f in lint_document(built) if f.severity is Severity.ERROR]

    def test_a_term_is_escaped(self):
        html = Glossary([Term("<b>T</b>", "a & b")]).render(_engine())
        assert "&lt;b&gt;T&lt;/b&gt;" in html and "a &amp; b" in html


class TestRefusals:
    def test_a_duplicate_term_is_refused(self):
        with pytest.raises(ValidationError, match="share the anchor"):
            Glossary([Term("Carry", "x"), Term("carry", "y")])

    @pytest.mark.parametrize(("term", "definition"), [("", "x"), ("x", " ")])
    def test_a_blank_term_or_definition_is_refused(self, term, definition):
        with pytest.raises(ValidationError):
            Term(term, definition)

    def test_an_empty_glossary_is_refused(self):
        with pytest.raises(ValidationError):
            Glossary([])

    def test_a_term_claiming_a_sections_anchor_is_refused(self):
        built = Email(FACTS)
        built.add_section(FullWidth(title="Carry", anchor="term-carry", content=TextBlock("x")))
        with pytest.raises(ValidationError, match="term-carry"):
            built.add_section(FullWidth(content=Glossary(TERMS)))


def _engine():
    from pyhermes.builder import TemplateEngine

    return TemplateEngine()
