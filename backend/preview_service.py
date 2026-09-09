"""Secure kkFileView preview URL generation."""

from base64 import b64encode
from urllib.parse import quote

from .config import KKFILEVIEW_URL, PREVIEW_PUBLIC_URL


class PreviewService:
    """Create short-lived, single-file links that kkFileView can retrieve."""

    def preview_url(self, app, payload, filename):
        ticket = app.kk_preview_serializer.dumps(payload)
        source = f"{PREVIEW_PUBLIC_URL}/api/preview-source/{quote(ticket, safe='')}/{quote(filename, safe='')}"
        encoded_source = quote(b64encode(source.encode("utf-8")).decode("ascii"), safe="")
        return f"{KKFILEVIEW_URL}/onlinePreview?url={encoded_source}&officePreviewType=pdf"


preview_service = PreviewService()
