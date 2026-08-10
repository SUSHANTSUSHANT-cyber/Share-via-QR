"""QR code generation service for the secure transfer workflow."""

from __future__ import annotations

import io
import logging

import qrcode
from qrcode.image.pil import PilImage

from utils.helpers import build_public_url

logger = logging.getLogger("qr_transfer_system")


class QRService:
    """Generate QR codes and public target URLs."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.logger = logger

    def build_qr_target_url(self, session_id: str) -> str:
        """Build a public upload target URL for the session."""
        return build_public_url(f"/upload/{session_id}")

    def generate_qr_png(self, session_id: str) -> bytes:
        """Generate a PNG-encoded QR code for the session upload URL."""
        target_url = self.build_qr_target_url(session_id)
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=10,
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        image = qr.make_image(fill_color="#14213d", back_color="white", image_factory=PilImage)

        with io.BytesIO() as output:
            image.save(output, format="PNG")
            png_bytes = output.getvalue()

        self.logger.info("QR generated for session %s", session_id)
        return png_bytes
