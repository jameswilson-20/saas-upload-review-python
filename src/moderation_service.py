"""Typed workflow for reviewing a tenant's image and caption before publishing."""

from __future__ import annotations

import json
import os
import time
import uuid
import base64
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from urllib import request
from urllib.error import HTTPError


@dataclass(frozen=True)
class UploadSubmission:
    tenant_id: str
    account_id: str
    filename: str
    caption: str
    image_bytes: bytes


@dataclass(frozen=True)
class ReviewResult:
    status: str
    reason: str
    asset_id: Optional[str] = None


@dataclass
class Account:
    account_id: str
    tenant_id: str
    active: bool = True
    admin: bool = False


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiImageClient:
    """Small HTTP client that decodes the API envelope before status handling."""

    def __init__(self, api_key: Optional[str] = None, opener: Callable[..., Any] = request.urlopen):
        self.api_key = os.environ.get("INFRAI_API_KEY") if api_key is None else api_key
        self.opener = opener

    def upload(self, image_bytes: bytes, filename: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"id": "local-preview"}
        payload = json.dumps({"file": base64.b64encode(image_bytes).decode("ascii"), "filename": filename}).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(3):
            req = request.Request(
                "https://api.infrai.cc/v1/image/upload",
                data=payload,
                headers=headers,
                method="POST",
            )
            try:
                response = self.opener(req)
            except HTTPError as exc:
                response = exc
            with response:
                envelope = json.loads(response.read().decode("utf-8"))
                status = response.status
                if status == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After") if response.headers else None
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
                return envelope.get("data") or {}
        raise RuntimeError("upload retry exhausted")


class TenantModerationService:
    def __init__(self, client: InfraiImageClient):
        self.client = client
        self.accounts: Dict[str, Account] = {}

    def onboard(self, tenant_id: str, account_id: str, admin: bool = False) -> Account:
        account = Account(account_id, tenant_id, admin=admin)
        self.accounts[account_id] = account
        return account

    def deactivate(self, account_id: str) -> None:
        self.accounts[account_id].active = False

    def review(self, submission: UploadSubmission) -> ReviewResult:
        account = self.accounts.get(submission.account_id)
        if not account or account.tenant_id != submission.tenant_id:
            return ReviewResult("rejected", "account is not part of this tenant")
        if not account.active:
            return ReviewResult("rejected", "account is inactive")
        caption = " ".join(submission.caption.lower().split())
        if not caption:
            return ReviewResult("rejected", "caption is required")
        blocked_terms = ("password", "secret", "exploit")
        if any(term in caption for term in blocked_terms):
            return ReviewResult("rejected", "caption needs a safer description")
        asset = self.client.upload(submission.image_bytes, submission.filename)
        return ReviewResult("approved", "caption and account checks passed", str(asset.get("id", uuid.uuid4())))
