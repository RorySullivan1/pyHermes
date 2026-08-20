#!/usr/bin/env python3
"""
Email Assembler — Builds complete emails from skeleton + containers + components

This module assembles HTML emails by:
1. Loading a base skeleton template with placeholder markers
2. Reading container definitions that define section layouts
3. Inserting components into container slots
4. Replacing all {{placeholder}} variables with actual values
5. Validating the final HTML size (< 102KB)
6. Writing the complete email HTML to disk

Example usage:
    from pathlib import Path
    from assembler import build_email

    config = {
        "campaign_name": "Weekly Market Wrap",
        "email_subject": "March 24-28 Review",
        ...
        "sections": [
            {
                "container_type": "kpi_strip",
                "components": {
                    "kpi_1": "markets/sp500",
                    "kpi_2": "markets/ust10y",
                    "kpi_3": "markets/vix"
                }
            },
            ...
        ]
    }

    output = Path("output.html")
    build_email(config, Path("../"), output)
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional


def strip_doc_comments(html: str) -> str:
    """
    Strip leading documentation comment blocks and commented-out variant
    blocks from snippet files.

    Containers and components start with a large <!-- ... --> documentation
    block that describes usage, slots, placeholders, etc. These comments
    contain literal SLOT markers and placeholder names that would be
    incorrectly matched during assembly. Components may also have
    commented-out variant blocks (e.g., "COMMENTED OUT: 4-STAT VARIANT").

    Args:
        html: Raw snippet HTML

    Returns:
        HTML with doc comments and commented-out variants removed
    """
    # Strip leading doc comment block. The non-greedy [\s\S]*? finds the first
    # --> whose trailing whitespace is followed by an HTML tag (<[^!]), skipping
    # over embedded <!-- SLOT: xxx --> references that have inner -->.
    stripped = re.sub(r"^\s*<!--[\s\S]*?-->\s*(?=<[^!])", "", html, count=1)
    # Strip any "COMMENTED OUT:" variant blocks
    stripped = re.sub(r"\n*<!-- COMMENTED OUT:[\s\S]*?-->", "", stripped)
    return stripped


def load_snippet(path: Path, strip_docs: bool = True) -> str:
    """
    Load a snippet file and return its contents.

    Args:
        path: Path to the HTML snippet file
        strip_docs: If True (default), strip leading documentation comments

    Returns:
        String contents of the file

    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Snippet not found: {path}")
    content = path.read_text(encoding="utf-8")
    if strip_docs:
        content = strip_doc_comments(content)
    return content


def insert_into_slot(container_html: str, slot_name: str, content: str) -> str:
    """
    Insert content into a named slot in container HTML.

    Looks for markers like <!-- SLOT: xxx --> and replaces them with content.

    Args:
        container_html: The container HTML template
        slot_name: Name of the slot (e.g., "kpi_1", "body", "component")
        content: The HTML content to insert

    Returns:
        Updated HTML with content inserted into the slot
    """
    pattern = f"<!-- SLOT: {slot_name} -->"
    if pattern not in container_html:
        # Slot not found, return unchanged
        return container_html

    # Replace the slot marker with the content
    return container_html.replace(pattern, content)


def replace_placeholders(html: str, values: Dict[str, str]) -> str:
    """
    Replace all {{placeholder}} markers with values from a dictionary.

    Args:
        html: The HTML template with {{placeholders}}
        values: Dictionary mapping placeholder names to replacement values

    Returns:
        HTML with all placeholders replaced
    """
    result = html
    for key, value in values.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result


def activate_section_title(container_html: str, title: str) -> str:
    """
    Uncomment/activate the section title in a container.

    Looks for a commented-out title block and uncomments it, inserting the title text.

    Args:
        container_html: The container HTML
        title: The section title text

    Returns:
        Container with title activated
    """
    # Pattern: <!-- TITLE_START --> ... <!-- TITLE_END -->
    pattern = r"<!-- TITLE_START -->(.*?)<!-- TITLE_END -->"

    def replace_title(match):
        # Extract the template and replace {{title}} placeholder
        title_template = match.group(1)
        return title_template.replace("{{section_title}}", title)

    return re.sub(pattern, replace_title, container_html, flags=re.DOTALL)


def apply_background_color(container_html: str, color: str) -> str:
    """
    Apply a background color override to a container.

    Looks for background-color and bgcolor attributes and updates them.

    Args:
        container_html: The container HTML
        color: The background color (e.g., "#E8E6E1")

    Returns:
        Container with background color updated
    """
    # Update inline style background-color
    container_html = re.sub(
        r"background-color:#[0-9A-Fa-f]{6}", f"background-color:{color}", container_html
    )

    # Update bgcolor attribute
    container_html = re.sub(r'bgcolor="#[0-9A-Fa-f]{6}"', f'bgcolor="{color}"', container_html)

    return container_html


def strip_unused_titles(html: str) -> str:
    """
    Remove any TITLE_START/TITLE_END blocks that still contain the
    unreplaced {{section_title}} placeholder (i.e., sections with no title).

    Args:
        html: The assembled HTML

    Returns:
        HTML with unused title blocks removed
    """
    pattern = r"<!-- TITLE_START -->.*?\{\{section_title\}\}.*?<!-- TITLE_END -->"
    return re.sub(pattern, "", html, flags=re.DOTALL)


def build_email(
    config: Dict[str, Any], base_dir: Optional[Path] = None, output_path: Path = Path("output.html")
) -> None:
    """
    Assemble a complete email from configuration.

    Args:
        config: Email configuration dictionary with keys:
            - metadata: campaign_name, email_subject, date_range, issue_label,
                       header_disclaimer, header_bg_image_url, logo_url, firm_name,
                       contact_description, contact_url, footer_disclaimer, current_year,
                       unsubscribe_url, view_in_browser_url, preheader_text
            - sections: List of section definitions, each with:
                - container_type: Name of container template (without .html),
                    looked up in templates/common/containers/
                - components: Dict mapping slot names to component paths
                    relative to templates/ (e.g., "analysis/kpi-strip",
                    "text/text-block"). The .html extension is appended.
                - title (optional): Section title
                - background_color (optional): Override background color
        base_dir: Base directory for templates (default: parent of svc/)
        output_path: Path to write the final HTML

    Raises:
        FileNotFoundError: If skeleton or template files not found
        ValueError: If final HTML exceeds 102KB
    """

    # Default base_dir to parent of svc/
    if base_dir is None:
        base_dir = Path(__file__).parent.parent

    base_dir = base_dir.resolve()

    # Load the skeleton (don't strip doc comments from skeleton)
    skeleton_path = base_dir / "templates" / "common" / "skeletons" / "base.html"
    skeleton = load_snippet(skeleton_path, strip_docs=False)

    # Assemble sections
    sections_html = ""
    for section_config in config.get("sections", []):
        container_type = section_config.get("container_type")
        components = section_config.get("components", {})
        title = section_config.get("title")
        bg_color = section_config.get("background_color")

        # Load container template
        container_path = base_dir / "templates" / "common" / "containers" / f"{container_type}.html"
        container = load_snippet(container_path)

        # Insert components into slots
        for slot_name, component_path in components.items():
            # Build component path (relative to templates/)
            comp_path = base_dir / "templates" / f"{component_path}.html"
            component_html = load_snippet(comp_path)

            # Insert into slot
            container = insert_into_slot(container, slot_name, component_html)

        # Activate section title if provided
        if title:
            container = activate_section_title(container, title)

        # Apply background color override if provided
        if bg_color:
            container = apply_background_color(container, bg_color)

        sections_html += container

    # Replace sections placeholder in skeleton
    skeleton = skeleton.replace("{{sections_placeholder}}", sections_html)

    # Strip any title blocks that weren't activated (still have {{section_title}})
    skeleton = strip_unused_titles(skeleton)

    # Collect all metadata and replace placeholders
    metadata = config.get("metadata", {})
    skeleton = replace_placeholders(skeleton, metadata)

    # Validate file size
    size_bytes = len(skeleton.encode("utf-8"))
    size_kb = size_bytes / 1024

    if size_kb > 102:
        raise ValueError(
            f"Final HTML is {size_kb:.1f}KB, exceeds 102KB limit. "
            f"Remove sections or reduce content."
        )

    # Print warning if over 90KB
    if size_kb > 90:
        print(f"WARNING: Email size is {size_kb:.1f}KB (target < 90KB)")
    else:
        print(f"Email size: {size_kb:.1f}KB (OK)")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(skeleton, encoding="utf-8")
    print(f"Email written to: {output_path}")


def main():
    """
    Example usage: Build a weekly market wrap email.

    This recreates the academic-financial-base.html layout using the
    modular skeleton + containers + components system.
    """

    # Define email configuration
    config = {
        "metadata": {
            # Skeleton placeholders
            "preheader_text": "Weekly perspective: equity markets, rates, and positioning for the week ahead.",
            "header_disclaimer": "For informational purposes only. Does not constitute investment advice.",
            "header_bg_image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&q=80&auto=format",
            "logo_url": "https://via.placeholder.com/90x36/FFFFFF/2C3E50?text=LOGO",
            "firm_name": "Research & Strategy",
            "campaign_name": "Weekly Market Perspective",
            "email_subject": "Weekly Market Perspective — March 24-28, 2026",
            "date_range": "March 24 – 28, 2026",
            "issue_label": "Vol. 4 · No. 13",
            "contact_description": "Our research and strategy team is available to discuss the themes covered in this report or answer questions about your portfolio.",
            "contact_url": "https://example.com/contact",
            "footer_disclaimer": "This material is provided for informational purposes only and does not constitute investment advice, an offer, or a solicitation. Past performance is not indicative of future results. For institutional and professional investor use only. Not for redistribution.",
            "current_year": "2026",
            "unsubscribe_url": "https://example.com/unsubscribe",
            "view_in_browser_url": "https://example.com/view-in-browser",
            # KPI strip placeholders
            "kpi_1_label": "S&P 500",
            "kpi_1_value": "5,234.18",
            "kpi_1_color": "#4A7C59",
            "kpi_1_sublabel": "+1.42% WoW",
            "kpi_2_label": "UST 10Y",
            "kpi_2_value": "4.28%",
            "kpi_2_color": "#B85450",
            "kpi_2_sublabel": "+6 bps",
            "kpi_3_label": "VIX",
            "kpi_3_value": "14.32",
            "kpi_3_color": "#4A7C59",
            "kpi_3_sublabel": "-2.18 pts",
            # Text block placeholders
            "text_content": "Equity markets advanced for the third consecutive week as cooling inflation data reinforced expectations that the Federal Reserve will begin easing policy later this quarter. The S&amp;P 500 posted a weekly gain of 1.42%, led by cyclical sectors, while breadth improved notably with the equal-weighted index outperforming its cap-weighted counterpart by 38 basis points. Treasuries sold off modestly, with the 10-year yield rising 6 basis points to 4.28%, as stronger-than-expected retail sales tempered rate-cut enthusiasm. Credit markets remained constructive, with investment-grade spreads tightening 3 basis points to 92 bps over Treasuries.",
            # Data table placeholders
            "col_1_header": "Asset Class",
            "col_2_header": "Level",
            "col_3_header": "WoW",
            "col_4_header": "YTD",
            "row_1_col1": "S&P 500",
            "row_1_col2": "5,234.18",
            "row_1_col2_color": "#5A5A5A",
            "row_1_col3": "+1.42%",
            "row_1_col3_color": "#4A7C59",
            "row_1_col4": "+8.73%",
            "row_1_col4_color": "#4A7C59",
            "row_2_col1": "US 10Y Treasury",
            "row_2_col2": "4.28%",
            "row_2_col2_color": "#5A5A5A",
            "row_2_col3": "+6 bps",
            "row_2_col3_color": "#B85450",
            "row_2_col4": "+22 bps",
            "row_2_col4_color": "#B85450",
            "row_3_col1": "IG Credit (OAS)",
            "row_3_col2": "92 bps",
            "row_3_col2_color": "#5A5A5A",
            "row_3_col3": "-3 bps",
            "row_3_col3_color": "#4A7C59",
            "row_3_col4": "-14 bps",
            "row_3_col4_color": "#4A7C59",
            "row_4_col1": "WTI Crude",
            "row_4_col2": "$78.42",
            "row_4_col2_color": "#5A5A5A",
            "row_4_col3": "-0.87%",
            "row_4_col3_color": "#B85450",
            "row_4_col4": "+4.21%",
            "row_4_col4_color": "#4A7C59",
            "table_source": "Source: Bloomberg",
            "table_as_of_date": "March 28, 2026",
            # Chart block placeholders
            "chart_image_url": "https://via.placeholder.com/536x300/F8F7F5/3B3B3B?text=Factor+Returns+Chart",
            "chart_alt_text": "Bar chart showing weekly factor returns across value, momentum, quality, and size factors",
            "chart_source": "Chart data: Bloomberg, internal calculations",
            # Numbered list placeholders
            "item_1_number": "1",
            "item_1_title": "Disinflation Trend Intact",
            "item_1_body": "Core PCE decelerated to 2.6% year-over-year, the lowest reading since early 2024. The three-month annualized rate fell to 2.3%, reinforcing the view that the disinflationary trend remains on track despite sticky shelter components.",
            "item_2_number": "2",
            "item_2_title": "Market Breadth Improving",
            "item_2_body": "The percentage of S&P 500 constituents trading above their 200-day moving average rose to 68%, up from 54% at the February low. Small-cap participation also improved, with the Russell 2000 outperforming large caps by 82 bps on the week.",
            "item_3_number": "3",
            "item_3_title": "Credit Spreads Signal Risk Appetite",
            "item_3_body": "Investment-grade credit spreads tightened to 92 bps, the lowest level since November 2024. High-yield spreads also compressed, falling 8 bps to 312 bps, suggesting healthy risk appetite and limited concern about near-term recession.",
            # Author placeholders
            "author_name": "Jonathan R. Mercer, CFA",
            "author_title": "Chief Market Strategist",
            "author_email": "j.mercer@example.com",
        },
        "sections": [
            # 1. KPI Strip — highlight container for visual separation
            {
                "container_type": "highlight",
                "title": "Market Snapshot",
                "components": {
                    "content": "analysis/kpi-strip",
                },
            },
            # 2. Narrative — full-width text block
            {
                "container_type": "full-width",
                "title": "Week in Review",
                "components": {
                    "content": "text/text-block",
                },
            },
            # 3. Data Table — full-width
            {
                "container_type": "full-width",
                "title": "Asset Class Returns",
                "components": {
                    "content": "analysis/data-table",
                },
            },
            # 4. Chart — full-width
            {
                "container_type": "full-width",
                "title": "Exhibit 1 — Factor Returns",
                "components": {
                    "content": "analysis/chart-block",
                },
            },
            # 5. Key Themes — full-width numbered list
            {
                "container_type": "full-width",
                "title": "Key Themes",
                "components": {
                    "content": "text/numbered-list",
                },
            },
            # 6. Closing + Author — full-width
            {
                "container_type": "full-width",
                "title": "Closing Remarks",
                "components": {
                    "content": "text/author-block",
                },
            },
        ],
    }

    # Build the email
    output = Path(__file__).parent.parent / "weekly_market_wrap_assembled.html"
    build_email(config, output_path=output)


if __name__ == "__main__":
    main()
