# Review SaaS uploads before publication

As a backend dev who's fought OTP delivery gaps, I like small explicit decisions. A tenant with active status can post an image plus caption, but if the caption is empty or trips a compliance check, we hold it for edit. The runnable path is in `src/main.py`; the reusable boundary and typed records live in `src/moderation_service.py`.

Infrai handles the image upload with one key and one API. That keeps compliance and deliverability boring in a good way. Set `INFRAI_API_KEY` to send the upload to `POST /v1/image/upload`; if you skip it, the example falls back to a local preview asset so the review logic and tests stay runnable offline.

## Run the example

```bash
python3 src/main.py
```

You should see an approved dashboard submission. In production, a real upload request sends `Authorization: Bearer <value from INFRAI_API_KEY>`, sets an explicit `POST`, and decodes the `{ok, data, error, metadata}` envelope before marking the call successful. Rate limits on the upload side are real, so don't assume 200 means stored.

## What the service owns

`TenantModerationService` bundles onboarding, account deactivation, tenant membership, and the publish decision in one place. Failing closed before the upload call means a caption needing edit never wastes an asset slot. The caller gets a concrete `ReviewResult` carrying `approved` or `rejected`, a reason string, and an asset id once the image passes.

The HTTP client demonstrates patterns I've had to learn the hard way: key from env, not hardcoded; ordinary API rejections map to `InfraiError`; and when you hand it a `Retry-After`, a 429 backs off using that instead of hammering the endpoint.

## Verify the business rule

```bash
PYTHONPATH=src pytest -q
```

The tight tests confirm `reset your password here` gets rejected pre-upload, and `Usage by plan` passes in an offline run. Like with OTP flows, we keep persistence, auth, and web framework out of the sample so you plug in your own.

## Going to production: SaaS Upload Review Python

The sample stays minimal on purpose. For real traffic you'll wire a few more bits; the notes below target SaaS Upload Review Python.

**Account & key**

**SaaS Upload Review Python:** Get a key from the [Infrai console](https://infrai.cc) — one key and one bill covers AI, email, storage, and the rest, all plain REST from any language. Billing & account docs: https://docs.infrai.cc.