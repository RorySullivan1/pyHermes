# Footer Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the footer into a structured, partially-flexible region (background, full-box border, optional image, optional disclaimer) and move the contact call-to-action out into a new `ContactBlock` body component.

**Architecture:** "Contact Us" becomes a `Component` placed in the body like any other. The footer becomes a single-slot region rendered in its own table below the body, so a border box is drawable. The disclaimer text moves onto the `Footer` object and is emitted unwrapped; the three legal facts stay on `EmailMetadata`. `MinimalFooter` and the two old footer templates are deleted (clean break).

**Tech Stack:** Python 3.13, Jinja2 (`StrictUndefined`, autoescape off), pytest, ruff, mypy. Templates ship inside the `svc.builder` package.

**Spec:** `docs/superpowers/specs/2026-08-26-footer-rework-design.md`

## Global Constraints

- **Import surface:** everything public imports from `svc.builder` / `svc.builder.models`. Add new public names to `svc/builder/__init__.py` `__all__`.
- **Validation at construction time** — models/components raise `ValidationError` from `__init__`, never from `context()`/render.
- **`StrictUndefined`** — every template variable must have a key in the component's/region's context dict, or the render raises. Inject falsey defaults; never `{% if x %}` on a name that may be undefined.
- **Autoescape is OFF.** Plain-text fields are escaped in templates via `| escape_html`. HTML fields (`disclaimer`, `TextBlock.content`) are emitted raw — caller's job to escape. Attributes (`src`, `href`, `alt`) are always `| escape_html`.
- **Hex colors** are `#RRGGBB`, validated by `models._validate_color`.
- **URL schemes** validated by `models._validate_url` (allows `http`, `https`, `mailto`, `cid`, relative).
- **102 KB Gmail limit** enforced by `Email._validate_size()`; warns at 90 KB.
- **Goldens are opt-in:** regenerate with `pytest --update-goldens`; never rewrite implicitly.
- **Test invocation:** the Gmail/Outlook adapter tests need optional deps not always installed. Run `pytest --ignore=tests/test_gmail.py --ignore=tests/test_outlook.py` when those are absent.

---

### Task 1: `ContactBlock` body component

**Files:**
- Create: `svc/builder/templates/text/contact-block.html`
- Modify: `svc/builder/components.py` (add `ContactBlock` after `TextBlock`)
- Modify: `svc/builder/__init__.py` (import + `__all__`)
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: `Component` base, `models._validate_url`, `exceptions.ValidationError`.
- Produces: `ContactBlock(heading: str, description: str = "", cta_label: str = "Contact Us", cta_url: str = "")`; `template_path = "text/contact-block.html"`; `context()` returns keys `contact_heading`, `contact_description`, `contact_cta_label`, `contact_url` (names kept from the old footer-contact template so its markup migrates unchanged).

- [ ] **Step 1: Write the failing tests**

In `tests/test_components.py`, add:

```python
from svc.builder import ContactBlock, FullWidth  # add to existing imports
from svc.builder.exceptions import ValidationError


class TestContactBlock:
    def test_requires_a_heading(self):
        with pytest.raises(ValidationError):
            ContactBlock(heading="", cta_url="https://x.com/contact")

    def test_requires_a_cta_url(self):
        with pytest.raises(ValidationError):
            ContactBlock(heading="Questions?", cta_url="")

    def test_rejects_an_unsafe_cta_url(self):
        with pytest.raises(ValidationError):
            ContactBlock(heading="Questions?", cta_url="javascript:alert(1)")

    def test_renders_the_dual_cta_and_escapes_text(self, engine):
        html = ContactBlock(
            "Questions & feedback?", "Ask the desk.", "Reach out", "https://x.com/contact"
        ).render(engine)
        assert "v:roundrect" in html           # Outlook button survives
        assert "https://x.com/contact" in html
        assert "Reach out" in html
        assert "Questions &amp; feedback?" in html   # escaped by the template
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_components.py::TestContactBlock -v`
Expected: FAIL — `ImportError: cannot import name 'ContactBlock'`.

- [ ] **Step 3: Create the template**

Create `svc/builder/templates/text/contact-block.html` — the inner card lifted from `regions/footer-contact.html`, minus its outer `<tr><td>` (the container supplies that):

```html
{# CONTACT CALL-TO-ACTION — a body component (was the footer's contact card). #}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid {{ theme.palette.rule }}; border-radius:4px;">
  <tr>
    <td style="padding:{{ size.component.contact_pad_y }}px {{ size.component.contact_pad_x }}px;">
      <p style="margin:0; font-family:Georgia,'Times New Roman',serif; font-size:{{ size.type.subheading }}px;
                font-weight:bold; color:{{ theme.text.heading }}; letter-spacing:0.2px;">
        {{ contact_heading | escape_html }}
      </p>
      <p style="margin:{{ size.component.contact_heading_gap }}px 0 {{ size.component.contact_cta_gap }}px; font-family:Arial,Helvetica,sans-serif; font-size:{{ size.type.secondary }}px;
                color:{{ theme.text.secondary }}; line-height:{{ size.component.contact_line | percent }};">
        {{ contact_description | escape_html }}
      </p>
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="{{ contact_url | escape_html }}"
        style="height:{{ size.component.cta_height }}px;v-text-anchor:middle;width:{{ size.component.cta_width }}px;" arcsize="8%"
        strokecolor="{{ theme.palette.accent }}" fillcolor="{{ theme.palette.accent }}">
        <w:anchorlock/>
        <center style="color:{{ theme.text.on_dark }};font-family:Arial,Helvetica,sans-serif;
                       font-size:{{ size.type.secondary }}px;font-weight:bold;">
          {{ contact_cta_label | escape_html }}
        </center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-->
      <a href="{{ contact_url | escape_html }}"
         style="background-color:{{ theme.palette.accent }}; border-radius:3px; color:{{ theme.text.on_dark }};
                display:inline-block; font-family:Arial,Helvetica,sans-serif;
                font-size:{{ size.type.secondary }}px; font-weight:bold; line-height:{{ size.component.cta_height }}px;
                text-align:center; text-decoration:none; width:{{ size.component.cta_width }}px;
                -webkit-text-size-adjust:none;">
        {{ contact_cta_label | escape_html }}
      </a>
      <!--<![endif]-->
    </td>
  </tr>
</table>
```

- [ ] **Step 4: Add the component**

In `svc/builder/components.py`, after the `TextBlock` class, add:

```python
class ContactBlock(Component):
    """
    A contact call-to-action card: heading, blurb, and a button.

    The body-component form of what used to be the footer's contact card.
    Placed like any component — ``FullWidth(content=ContactBlock(...))`` —
    typically as the last section. Owns the Outlook ``v:roundrect`` / anchor
    dual button. Validates at construction, like every model here.
    """

    template_path = "text/contact-block.html"

    def __init__(
        self,
        heading: str,
        description: str = "",
        cta_label: str = "Contact Us",
        cta_url: str = "",
    ):
        if not heading:
            raise ValidationError("ContactBlock requires a heading.")
        if not cta_url:
            raise ValidationError("ContactBlock requires a cta_url.")
        _validate_url(cta_url, "ContactBlock.cta_url")
        self.heading = heading
        self.description = description
        self.cta_label = cta_label
        self.cta_url = cta_url

    def context(self) -> dict[str, Any]:
        return {
            "contact_heading": self.heading,
            "contact_description": self.description,
            "contact_cta_label": self.cta_label,
            "contact_url": self.cta_url,
        }
```

`_validate_url` is already imported at the top of `components.py` (`from .models import ... _validate_url`).

- [ ] **Step 5: Export it**

In `svc/builder/__init__.py`, add `ContactBlock` to the `from .components import (...)` block and to `__all__` (alphabetical-ish, next to the other components).

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_components.py::TestContactBlock -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add svc/builder/templates/text/contact-block.html svc/builder/components.py svc/builder/__init__.py tests/test_components.py
git commit -m "Add ContactBlock body component"
```

---

### Task 2: Footer core swap (region + templates + base.html + metadata)

Atomic: the suite is red between the first and last step of this task because `EmailMetadata._hydrate` and `Footer`'s fields must change together.

**Files:**
- Modify: `svc/builder/regions.py` (rework `Footer`, delete `MinimalFooter`)
- Create: `svc/builder/templates/regions/footer.html`
- Delete: `svc/builder/templates/regions/footer-contact.html`, `svc/builder/templates/regions/footer-legal.html`
- Modify: `svc/builder/templates/base.html` (two slots → one)
- Modify: `svc/builder/models.py` (`EmailMetadata`: remove fields/InitVars, update `FOOTER_FACTS`, `_hydrate`, docstring)
- Modify: `svc/builder/__init__.py` (drop `MinimalFooter`)
- Test: `tests/test_footer.py` (rewrite), `tests/test_models.py`, `tests/test_metadata_parameters.py`, `tests/test_regions.py`

**Interfaces:**
- Consumes: `Region` base (`context`, `render_slots`, `images`, `assets`), `models._validate_url`, `models._validate_color`.
- Produces: `Footer(background_color="", border=False, border_color="", image="", image_alt="", image_width=None, disclaimer="", unsubscribe_label="Unsubscribe", view_in_browser_label="View in browser")`; `SLOTS=("footer",)`; fills skeleton var `footer_html`. `EmailMetadata.FOOTER_FACTS = ("firm_name", "current_year", "unsubscribe_url", "view_in_browser_url")`. `MinimalFooter` no longer exists.

- [ ] **Step 1: Rewrite the footer test module (failing)**

Replace the body of `tests/test_footer.py` with tests for the new shape:

```python
"""The reworked footer region: one slot, structured presentation, optional disclaimer."""

import pytest

from svc.builder import Email, EmailBuilder, Footer, FullWidth, TextBlock
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage
from svc.builder.models import EmailMetadata

TEMPLATE_DIR = TemplateEngine().template_dir


def _render(footer: Footer | None = None) -> str:
    builder = EmailBuilder().metadata(
        {"email_subject": "S", "firm_name": "F", "campaign_name": "c", "current_year": "2026"}
    )
    if footer is not None:
        builder.footer(footer)
    return builder.section(FullWidth(content=TextBlock("<p>Body.</p>"))).render()


class TestFooterStructure:
    def test_base_html_has_one_footer_slot(self):
        base = (TEMPLATE_DIR / "base.html").read_text(encoding="utf-8")
        assert "{{ footer_html }}" in base
        assert "{{ footer_contact_html }}" not in base
        assert "{{ footer_legal_html }}" not in base

    def test_old_templates_are_gone(self):
        assert not (TEMPLATE_DIR / "regions" / "footer-contact.html").exists()
        assert not (TEMPLATE_DIR / "regions" / "footer-legal.html").exists()
        assert (TEMPLATE_DIR / "regions" / "footer.html").is_file()

    def test_copyright_and_links_always_render(self):
        html = _render()
        assert "&copy;" in html and "2026" in html
        assert "Unsubscribe" in html and "View in browser" in html


class TestDisclaimer:
    def test_empty_disclaimer_omits_the_line(self):
        assert "fine-print-marker" not in _render(Footer())  # no disclaimer text present

    def test_block_disclaimer_renders_without_breaking_its_wrapper(self):
        # The #3 regression: a <p> disclaimer must NOT sit inside a <p>.
        html = _render(Footer(disclaimer="<p>Not advice.</p>"))
        assert "<p>Not advice.</p>" in html
        legal = html.split("/Main container")[1]
        assert "<p>\n                <p>" not in legal  # no nested <p><p>


class TestPresentation:
    def test_border_adds_a_box(self):
        assert "border:1px solid" in _render(Footer(border=True))

    def test_background_color_is_applied_and_validated(self):
        assert "#123456" in _render(Footer(background_color="#123456"))
        with pytest.raises(ValidationError):
            Footer(background_color="red")

    def test_image_renders_and_enters_the_manifest(self, png_bytes):
        footer = Footer(image=EmailImage.attached(png_bytes, alt="Sign-off", width=100))
        html = _render(footer)
        assert 'alt="Sign-off"' in html and 'width="100"' in html
        assert footer.assets(), "attached footer image must reach the asset manifest"

    def test_image_width_falls_back_to_default(self, png_bytes):
        footer = Footer(image=EmailImage.attached(png_bytes, alt="x"))
        assert 'width="120"' in _render(footer)


class TestMinimalFooterIsGone:
    def test_it_is_no_longer_importable(self):
        with pytest.raises(ImportError):
            from svc.builder import MinimalFooter  # noqa: F401
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_footer.py -v`
Expected: FAIL (import/attribute errors — `Footer` still has old fields, `MinimalFooter` still exported, slots not collapsed).

- [ ] **Step 3: Rework the `Footer` class**

In `svc/builder/regions.py`: add `_validate_color` to the models import (`from .models import _validate_color, _validate_url`). Replace the `Footer` class body and **delete `MinimalFooter` entirely** with:

```python
@dataclass
class Footer(Region):
    """
    The closing region: a structured, partially-flexible block.

    The caller controls its background, an optional full-box border, an
    optional sign-off image, the disclaimer text, and the two link labels.
    It does not control fonts or geometry. The copyright year, firm name and
    the two outbound URLs are facts about the email and arrive via
    :meth:`context`. The disclaimer is optional — an empty one omits the
    fine-print line; the copyright + links line always renders.

    Attributes:
        background_color: Hex override; empty falls back to the theme surface.
        border:           Draw a full box around the footer.
        border_color:     Hex; empty falls back to the theme rule colour.
        image:            Optional sign-off mark (URL or EmailImage), rendered
                          above the copyright line.
        image_alt:        Alt text; falls back to the EmailImage's own alt.
        image_width:      Display width in px; falls back to the EmailImage's
                          own width, then to :data:`DEFAULT_IMAGE_WIDTH`.
        disclaimer:       Free-form HTML, emitted **raw and unwrapped**.
        unsubscribe_label / view_in_browser_label: link wording.
    """

    CONTEXT_NAME: ClassVar[str] = "footer"
    SLOTS: ClassVar[tuple[str, ...]] = ("footer",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"footer": "regions/footer.html"}
    REQUIRED_SLOTS: ClassVar[tuple[str, ...]] = ("footer",)
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("image",)
    DEFAULT_IMAGE_WIDTH: ClassVar[int] = 120

    background_color: str = ""
    border: bool = False
    border_color: str = ""
    image: "str | EmailImage" = ""
    image_alt: str = ""
    image_width: int | None = None
    disclaimer: str = ""
    unsubscribe_label: str = "Unsubscribe"
    view_in_browser_label: str = "View in browser"

    def validate(self) -> None:
        super().validate()
        for name in ("background_color", "border_color"):
            value = getattr(self, name)
            if value:
                _validate_color(value, f"footer.{name}")
        if self.image_width is not None and self.image_width <= 0:
            raise ValidationError(f"'footer.image_width' must be positive, got: {self.image_width}")

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        resolved = {
            "image_alt": self.resolved_image_alt(),
            "image_width": self.resolved_image_width(),
        }
        return {**super().context({}), **resolved, **facts}

    def resolved_image_alt(self) -> str:
        from .images import EmailImage

        if self.image_alt:
            return self.image_alt
        if isinstance(self.image, EmailImage) and self.image.alt:
            return self.image.alt
        return ""

    def resolved_image_width(self) -> int:
        from .images import EmailImage

        if self.image_width is not None:
            return self.image_width
        if isinstance(self.image, EmailImage) and self.image.width is not None:
            return self.image.width
        return self.DEFAULT_IMAGE_WIDTH
```

- [ ] **Step 4: Create `regions/footer.html`**

Create `svc/builder/templates/regions/footer.html`. The disclaimer sits in a `<div>` (not a `<p>`) so block content can't break its wrapper — the fix for problem #3:

```html
{#
  FOOTER REGION — one self-contained table below the body.

  Presentation is a parameter here (unlike containers): background_color, an
  optional full box, and an optional sign-off image. The disclaimer is raw and
  UNWRAPPED — a <div>, never a <p> — so caller HTML renders correctly. The
  copyright + links line always renders. Square corners: Outlook ignores
  border-radius, so the box is a plain solid border.

  Context: background_color, border, border_color, image, image_alt,
  image_width, disclaimer, unsubscribe_label, view_in_browser_label (region);
  firm_name, current_year, unsubscribe_url, view_in_browser_url (facts).
#}
        <table role="presentation" width="{{ size.frame.width }}" cellpadding="0" cellspacing="0" border="0"
               style="max-width:{{ size.frame.width }}px; background-color:{{ background_color | default(theme.palette.wrapper_bg, true) }};" bgcolor="{{ background_color | default(theme.palette.wrapper_bg, true) }}" class="email-container">
          <tr>
            <td style="padding:{{ size.space.footer_legal_top }}px {{ size.frame.pad_x }}px {{ size.space.footer_copyright_bottom }}px;{% if border %} border:1px solid {{ border_color | default(theme.palette.rule, true) }};{% endif %} background-color:{{ background_color | default(theme.palette.wrapper_bg, true) }};" bgcolor="{{ background_color | default(theme.palette.wrapper_bg, true) }}">
{% if image %}
              <p style="margin:0 0 {{ size.space.footer_legal_top }}px; text-align:center;">
                <img src="{{ image | escape_html }}" alt="{{ image_alt | escape_html }}" width="{{ image_width }}" style="display:inline-block; border:0; height:auto;">
              </p>
{% endif %}
{% if disclaimer %}
              <div style="font-family:Arial,Helvetica,sans-serif; font-size:{{ size.type.micro }}px;
                          color:{{ theme.text.fine_print }}; line-height:{{ size.component.legal_line | percent }}; text-align:center;">
                {{ disclaimer }}
              </div>
{% endif %}
              <p style="margin:{{ size.space.footer_copyright_top }}px 0 0; font-family:Arial,Helvetica,sans-serif; font-size:{{ size.type.micro }}px;
                        color:{{ theme.text.light }}; text-align:center;">
                &copy; {{ current_year | escape_html }} {{ firm_name | escape_html }} &nbsp;&middot;&nbsp;
                <a href="{{ unsubscribe_url | escape_html }}" style="color:{{ theme.palette.accent }}; text-decoration:underline;">{{ unsubscribe_label | escape_html }}</a>
                &nbsp;&middot;&nbsp;
                <a href="{{ view_in_browser_url | escape_html }}" style="color:{{ theme.palette.accent }}; text-decoration:underline;">{{ view_in_browser_label | escape_html }}</a>
              </p>
            </td>
          </tr>
        </table>
```

- [ ] **Step 5: Collapse the base.html slots**

In `svc/builder/templates/base.html`, replace the footer comment block and the two slot lines (the `{{ footer_contact_html }}` … `{{ footer_legal_html }}` region, currently lines ~93–106) with:

```html
        </table>
        <!-- /Main container -->

{# The footer renders as one self-contained table below the body. It sits at
   column 0: an indented {{ }} would prepend that indentation to the fragment's
   first line only, and the region carries its own. #}
{{ footer_html }}
```

Delete the old two-slot comment. Delete the old files:

```bash
git rm svc/builder/templates/regions/footer-contact.html svc/builder/templates/regions/footer-legal.html
```

- [ ] **Step 6: Migrate `EmailMetadata`**

In `svc/builder/models.py`:
- Delete the fields `contact_url` and `footer_disclaimer`.
- Delete the InitVars `contact_heading`, `contact_description`, `contact_cta_label` (keep `unsubscribe_label`, `view_in_browser_label`).
- Update `__post_init__`'s signature to drop the three `contact_*` parameters, and update the footer `_hydrate` legacy dict to:

```python
        self.footer = self._hydrate(
            Footer,
            "footer",
            {
                "unsubscribe_label": unsubscribe_label,
                "view_in_browser_label": view_in_browser_label,
            },
        )
```

- Update `FOOTER_FACTS` to exactly:

```python
    FOOTER_FACTS = (
        "firm_name",
        "current_year",
        "unsubscribe_url",
        "view_in_browser_url",
    )
```

- Update the class docstring paragraph about footer fields to reflect that the disclaimer and contact copy no longer live here (the disclaimer is on `Footer`; the contact card is a `ContactBlock` body component).

- [ ] **Step 7: Drop `MinimalFooter` from the public API**

In `svc/builder/__init__.py`, remove `MinimalFooter` from the `from .regions import (...)` block and from `__all__`.

- [ ] **Step 8: Update the sibling tests**

- `tests/test_models.py`: remove any assertion referencing `footer_disclaimer` or `contact_url` as `EmailMetadata` fields; update a `FOOTER_FACTS` expectation to the four-tuple above.
- `tests/test_metadata_parameters.py`: delete tests that pass `contact_heading` / `contact_description` / `contact_cta_label` / `contact_url` / `footer_disclaimer` as flat metadata keywords; keep the `unsubscribe_label` / `view_in_browser_label` hydration tests.
- `tests/test_regions.py`: remove `MinimalFooter` import and its tests; if a general Footer construction test asserted old fields, update it to the new field set.

- [ ] **Step 9: Run the affected tests**

Run: `pytest tests/test_footer.py tests/test_models.py tests/test_metadata_parameters.py tests/test_regions.py -v`
Expected: PASS.

- [ ] **Step 10: Run the whole suite (goldens will still be stale — expected)**

Run: `pytest --ignore=tests/test_gmail.py --ignore=tests/test_outlook.py -q`
Expected: failures ONLY in `tests/test_goldens.py` / `tests/test_fixtures.py` (rendered output changed; fixed in Task 3). If anything else fails, fix it before committing.

- [ ] **Step 11: Commit**

```bash
git add svc/builder tests/test_footer.py tests/test_models.py tests/test_metadata_parameters.py tests/test_regions.py
git commit -m "Rework footer into a single structured region; drop MinimalFooter"
```

---

### Task 3: Fixtures & goldens

**Files:**
- Modify: `qa/fixtures/kitchen_sink.py` (add a `ContactBlock` section; set a `Footer` exercising the new fields)
- Modify: `qa/fixtures/minimal_footer.py` (repurpose to exercise `border` / `background_color` / `image`)
- Regenerate: `qa/fixtures/goldens/*.html` + `*.assets.txt`

**Interfaces:**
- Consumes: `ContactBlock` (Task 1), reworked `Footer` (Task 2).
- Produces: updated goldens the drift gate accepts.

- [ ] **Step 1: Add `ContactBlock` to the kitchen sink**

In `qa/fixtures/kitchen_sink.py`, add `ContactBlock` to the `svc.builder` import, and add a final section before `.build()`:

```python
        .section(
            FullWidth(
                content=ContactBlock(
                    heading="Questions or feedback?",
                    description="Reach the research desk any time.",
                    cta_label="Contact the desk",
                    cta_url="https://example.com/contact",
                )
            )
        )
```

The `TestKitchenSinkCompleteness` test in `tests/test_fixtures.py` requires every `Component` subclass to appear here, so this addition is what keeps that test green now that `ContactBlock` exists.

- [ ] **Step 2: Repurpose the footer fixture**

In `qa/fixtures/minimal_footer.py`, replace the `MinimalFooter(...)` usage with a `Footer` that exercises the new surface (import `Footer`, `EmailImage`, and the fixture PNG helper already used elsewhere in `qa/fixtures/`):

```python
    .footer(
        Footer(
            background_color="#F2F1EE",
            border=True,
            image=EmailImage.attached(solid_png(96, 96, (42, 61, 84)), alt="Sign-off", width=96),
            disclaimer="<p>For illustrative purposes only. Not investment advice.</p>",
        )
    )
```

If the fixture's module docstring names `MinimalFooter`, update it to describe the structured footer.

- [ ] **Step 3: Regenerate goldens**

Run: `pytest --update-goldens --ignore=tests/test_gmail.py --ignore=tests/test_outlook.py -q`
Expected: PASS. Then inspect `git status qa/fixtures/goldens/` — the diff should be footer-region changes plus the new kitchen-sink contact section, and nothing spurious.

- [ ] **Step 4: Verify the drift gate is green**

Run: `pytest --ignore=tests/test_gmail.py --ignore=tests/test_outlook.py -q`
Expected: PASS (full suite, goldens included).

- [ ] **Step 5: Commit**

```bash
git add qa/fixtures
git commit -m "Update fixtures and goldens for the reworked footer and ContactBlock"
```

---

### Task 4: Update the examples

**Files:**
- Modify: `examples/market-snapshot/market-snapshot.py` (+ its `.html`)
- Modify: `examples/research-brief/research-brief.py` (+ its `.html`)

**Interfaces:**
- Consumes: reworked `Footer` (disclaimer now on the region, not metadata), `ContactBlock`.

- [ ] **Step 1: Migrate `market-snapshot`**

The `footer_disclaimer` metadata key no longer exists — passing it now raises. Remove it from the `metadata({...})` dict and set the disclaimer on the footer instead, as **inline text** (not a `<p>`, which was the original bug):

```python
from svc.builder import Footer  # add to imports
# ...in build(), after .metadata(...):
        .footer(Footer(disclaimer="For illustrative purposes only. Not investment advice."))
```

- [ ] **Step 2: Migrate `research-brief` and add a `ContactBlock`**

Same disclaimer migration, plus demonstrate the new component — add a final section:

```python
from svc.builder import ContactBlock  # add to imports
# ...last section before .build():
        .section(
            FullWidth(
                content=ContactBlock(
                    heading="Questions about this note?",
                    description="Reach the research desk.",
                    cta_label="Email the desk",
                    cta_url="mailto:research@example.com",
                )
            )
        )
```

- [ ] **Step 3: Rebuild both and verify size**

Run:
```bash
python examples/market-snapshot/market-snapshot.py
python examples/research-brief/research-brief.py
```
Expected: each prints `Email size: … (OK)` and rewrites its `.html`. Open one in a browser to confirm the disclaimer now renders small/light (no nested-`<p>` blowup) and the contact card appears.

- [ ] **Step 4: Commit**

```bash
git add examples
git commit -m "Update examples for the reworked footer and ContactBlock"
```

---

### Task 5: Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:** none (docs only).

- [ ] **Step 1: Update `CLAUDE.md`**

- In the components list, add `ContactBlock`; in the containers/regions description, change the footer to "single region, one slot (`footer_html`)" and remove `MinimalFooter`.
- In the "Public API" import example, add `ContactBlock`, drop `MinimalFooter`.
- Update the footer's ownership paragraph: disclaimer lives on `Footer`; the contact CTA is a body component; the footer no longer has a compliance floor.
- In the directory map, note `text/contact-block.html` and `regions/footer.html`; drop `regions/footer-contact.html` / `footer-legal.html`.

- [ ] **Step 2: Update `README.md`**

Update the composition section that describes the footer region (two slots → one; contact card is now a body component; disclaimer optional).

- [ ] **Step 3: Verify no stale references remain**

Run: `grep -rn "MinimalFooter\|footer_contact_html\|footer_legal_html\|footer_disclaimer" CLAUDE.md README.md svc/ examples/`
Expected: no matches (all migrated).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "Document the reworked footer and ContactBlock"
```

---

## Final verification

- [ ] `pytest --ignore=tests/test_gmail.py --ignore=tests/test_outlook.py -q` — full suite green.
- [ ] `ruff check . && ruff format --check .` — clean.
- [ ] `python -m mypy` — clean (use `python -m`, not the PATH `mypy`, per the epic's gotcha).
- [ ] Open both example `.html` files in a browser — footer box/image/disclaimer render as intended.

## Self-review notes (coverage against the spec)

- Spec §5 (`ContactBlock`) → Task 1. §6 (`Footer` fields/render/box) → Task 2 Steps 3–4. §7 (`base.html`) → Task 2 Step 5. §8 (`EmailMetadata`) → Task 2 Step 6. §9 (escaping/validation) → Task 1 Step 4 + Task 2 Step 3 (`_validate_color`, `_validate_url`, raw unwrapped disclaimer). §10 (migration) → Tasks 2–5. §11 (testing) → Task 1 Step 1, Task 2 Step 1, Task 3. §12 decisions are baked into the field defaults and template (text links, square corners, `border=False`, width 120, hard-removes).
- Type consistency: `Footer` field names and `FOOTER_FACTS` used identically in Task 2 and Task 3; `ContactBlock` signature identical in Tasks 1, 3, 4.
- Note: this branch also carries the unrelated `columns.html`/`sizing.py`/goldens fix and the initial `examples/` from earlier work — commit or split those separately from the footer tasks.
