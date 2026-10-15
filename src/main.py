import base64

from moderation_service import InfraiImageClient, TenantModerationService, UploadSubmission


EXAMPLE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lZkAAAAASUVORK5CYII="
)


def main() -> None:
    service = TenantModerationService(InfraiImageClient())
    service.onboard("acme", "editor-1")
    result = service.review(
        UploadSubmission("acme", "editor-1", "dashboard.png", "Quarterly pipeline dashboard", EXAMPLE_PNG)
    )
    print(f"{result.status}: {result.reason} (asset={result.asset_id})")


if __name__ == "__main__":
    main()
