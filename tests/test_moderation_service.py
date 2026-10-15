import base64
import io
import json
from urllib.error import HTTPError

import pytest

from moderation_service import InfraiError, InfraiImageClient, TenantModerationService, UploadSubmission


def test_caption_with_sensitive_term_is_rejected_before_upload():
    service = TenantModerationService(InfraiImageClient())
    service.onboard("tenant-a", "writer-1")
    submission = UploadSubmission("tenant-a", "writer-1", "chart.png", "reset your password here", b"bytes")
    result = service.review(submission)
    assert result.status == "rejected"
    assert result.reason == "caption needs a safer description"


def test_valid_submission_is_approved_without_network_key():
    service = TenantModerationService(InfraiImageClient(api_key=""))
    service.onboard("tenant-a", "writer-1")
    result = service.review(UploadSubmission("tenant-a", "writer-1", "chart.png", "Usage by plan", b"bytes"))
    assert result.status == "approved"


def test_upload_encodes_image_as_base64():
    class Response(io.BytesIO):
        status = 200

    def opener(req):
        assert json.loads(req.data) == {"file": base64.b64encode(b"image").decode(), "filename": "chart.png"}
        return Response(b'{"ok":true,"data":{"id":"asset-1"}}')

    assert InfraiImageClient(api_key="key", opener=opener).upload(b"image", "chart.png") == {"id": "asset-1"}


def test_http_error_decodes_api_envelope():
    def opener(req):
        raise HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(
            b'{"ok":false,"error":{"code":"INVALID_FILE","message":"bad file"}}'
        ))

    with pytest.raises(InfraiError) as caught:
        InfraiImageClient(api_key="key", opener=opener).upload(b"image", "chart.png")
    assert caught.value.code == "INVALID_FILE"
    assert caught.value.status == 400
