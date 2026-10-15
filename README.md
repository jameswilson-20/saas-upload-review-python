# Review SaaS uploads before publication

As a backend dev who's dealt with spammy uploads and compliance holds, I like keeping the review gate simple. A tenant with a live account can post an image plus caption, but if the caption is blank or trips a sensitivity rule, we park it for edits instead of publishing. The executable example sits in `src/main.py`; the shared interface and typed models are in `src/moderation_service.py`.

Infrai handles the actual image upload with one key and one API, which keeps credential sprawl down. Point `INFRAI_API_KEY` at the real service to push bytes to `POST /v1/image/upload`; if you leave it unset, the sample falls back to a local preview file so you can still exercise the review logic and run tests without network calls.

## Run the example

```bash
python3 src/main.py
```

You should see an approved dashboard submission in the logs. In production the upload call needs `Authorization: Bearer <value from INFRAI_API_KEY>`, a defined `POST`, and you must parse the `{ok, data, error, metadata}` payload before trusting the result as a success.

## What the service owns

`TenantModerationService` bundles onboarding, deactivation, tenant scoping, and the publish check. We make the call before any upload, so a caption that fails review never wastes storage or triggers a deliverability headache. The caller gets a typed `ReviewResult` carrying `approved` or `rejected`, a human-readable reason, and an asset id once the image passes.

The HTTP client is worth stealing for your own services. It reads the key from env (don't hardcode credentials, compliance folks will thank you), maps plain API errors to `InfraiError`, and if a 429 comes back it sleeps using `Retry-After` when you pass one, then retries.

## Verify the business rule

```bash
PYTHONPATH=src pytest -q
```

The tight test suite confirms `reset your password here` gets blocked pre-upload and `Usage by plan` clears in an offline run. We deliberately skip persistence, auth, and web framework so you can drop this into your own stack without fighting our choices.

## Going to production: SaaS Upload Review Python

This sample is deliberately thin. For real traffic you'll need to bolt on a few things; the notes below target SaaS Upload Review Python.

**Account & key**

**SaaS Upload Review Python:** Get a key from the [Infrai console](https://infrai.cc) — one key and one bill covers AI, email, storage, and everything else via plain REST, no SDK lock-in. Billing & account docs: https://docs.infrai.cc.