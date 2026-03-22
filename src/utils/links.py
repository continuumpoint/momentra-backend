from src.config.settings import get_settings

settings = get_settings()


def build_upload_link(event_id: str, base_url: str) -> str:
    return f"{base_url}upload/{event_id}"


def build_gallery_link(event_id: str, base_url: str) -> str:
    return f"{base_url}gallery/{event_id}"
