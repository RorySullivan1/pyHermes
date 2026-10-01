"""
The human check for #279: put a real email into classic Outlook's drafts on Windows.

    pip install -e ".[outlook-desktop]"
    python -m qa.outlook_desktop_check you@example.com

Builds ``surfaced_layout`` with an attached image, creates the draft and opens
it. Nothing is sent. Record what you see in `.claude/context/verification-surface.md`.
"""

from __future__ import annotations

import sys

from pyhermes.builder import FullWidth, ImageBlock
from pyhermes.builder.images import EmailImage
from pyhermes.delivery import build_message
from pyhermes.outlook.desktop import create_draft

from .fixtures import surfaced_layout
from .fixtures._png import solid_png

QUESTIONS = (
    "1. The draft opened in Outlook, and nothing was sent.",
    "2. The navy band's title and text are light and readable.",
    "3. The 120x40 teal rectangle shows inline under the last section, not as a paperclip.",
    "4. The attachment well is empty: the picture is hidden, not listed.",
    "5. The three coloured callouts and the two buttons render.",
)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m qa.outlook_desktop_check you@example.com", file=sys.stderr)
        return 2
    email = surfaced_layout.build()
    image = EmailImage.attached(solid_png(120, 40, (91, 138, 154)), alt="Teal check", width=120)
    email.add_section(FullWidth(ImageBlock(image), title="Inline image check"))
    message = build_message(email, sender=argv[0], to=[argv[0]])
    create_draft(message)
    print("Draft created. Check, and record the answers:")
    print("\n".join(QUESTIONS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
