"""
The URL fetcher: a document's own manifest, and nothing else.

WeasyPrint resolves every ``src`` and ``url()`` through a fetcher. This one
serves ``cid:`` references out of the asset manifest the builder already
declares, and refuses everything else — so a build cannot quietly reach the
network for an image a caller forgot to attach.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - weasyprint is an optional extra
    from pyhermes.builder.images import ImageAsset

from .exceptions import UnreachableResourceError

#: The scheme this exporter serves from the manifest.
SERVED_SCHEME = "cid:"

#: The one other scheme that resolves without a request. A ``data:`` URI
#: *is* its own bytes, so refusing it would reject an inlined image for not
#: being an attachment — two ways of carrying an image, both offline.
INLINE_SCHEME = "data:"


def build_fetcher(assets: list[ImageAsset]) -> Any:
    """
    A WeasyPrint URL fetcher bound to ``assets``.

    Built here rather than at import time because it subclasses a WeasyPrint
    type, and WeasyPrint is an optional extra: importing this module must not
    require it.

    Two settings carry the policy rather than leaving it to convention.
    ``allowed_protocols=("data",)`` means the inherited opener can reach
    nothing but an inline URI — no HTTP handler, no file handler — so a URL
    this fetcher does not recognise has nowhere to go even if the explicit
    refusal below were removed. ``fail_on_errors=True`` makes a refusal
    **stop the render**: WeasyPrint's default is to warn and carry on, which
    would drop a chart out of a compliance document and still hand back a
    PDF that looks finished.
    """
    from weasyprint.urls import URLFetcher, URLFetcherResponse

    by_content_id = {asset.content_id: asset for asset in assets}

    class ManifestFetcher(URLFetcher):
        """Serves the document's own attachments; refuses every other URL."""

        def __init__(self) -> None:
            super().__init__(allowed_protocols=("data",), fail_on_errors=True)

        def fetch(self, url: str, headers: Any = None) -> Any:
            if url.startswith(INLINE_SCHEME):
                # Its own bytes; the inherited data handler decodes them.
                return super().fetch(url, headers)
            if not url.startswith(SERVED_SCHEME):
                raise UnreachableResourceError(
                    f"{url!r} is not in this document's asset manifest, and the PDF "
                    "exporter makes no network requests. Attach the bytes with "
                    "EmailImage.attached() or inline them with EmailImage.inline()."
                )
            content_id = url[len(SERVED_SCHEME) :]
            asset = by_content_id.get(content_id)
            if asset is None:
                raise UnreachableResourceError(
                    f"{url!r} has no entry in the asset manifest. Every cid: "
                    "reference must be declared -- see the images() rule."
                )
            return URLFetcherResponse(
                url, body=asset.data, headers={"Content-Type": asset.mime_type}
            )

    return ManifestFetcher()
