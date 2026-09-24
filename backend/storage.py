import logging
from pathlib import Path
from . import config

logger = logging.getLogger("panorama.storage")


def is_cloud_storage_enabled() -> bool:
    """Check if Cloudinary cloud storage is configured."""
    return bool(
        config.CLOUDINARY_URL
        or (
            config.CLOUDINARY_CLOUD_NAME
            and config.CLOUDINARY_API_KEY
            and config.CLOUDINARY_API_SECRET
        )
    )


def init_storage():
    """Initialize storage backend (Cloudinary or local directory)."""
    if is_cloud_storage_enabled():
        import cloudinary

        if config.CLOUDINARY_URL:
            cloudinary.config()
        else:
            cloudinary.config(
                cloud_name=config.CLOUDINARY_CLOUD_NAME,
                api_key=config.CLOUDINARY_API_KEY,
                api_secret=config.CLOUDINARY_API_SECRET,
                secure=True,
            )
        logger.info("Cloudinary storage enabled for permanent 360 photo hosting.")
    else:
        config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Local storage enabled at %s", config.UPLOADS_DIR)


def upload_asset(file_path: Path | str, folder: str = "virtual_room_360", public_id: str | None = None) -> str:
    """
    Upload an image asset.
    If Cloudinary is configured, uploads and returns the secure HTTPS CDN URL.
    Otherwise, returns the path relative to config.UPLOADS_DIR.
    """
    path = Path(file_path)
    if is_cloud_storage_enabled():
        import cloudinary.uploader

        upload_opts = {
            "folder": folder,
            "resource_type": "image",
            "overwrite": True,
        }
        if public_id:
            upload_opts["public_id"] = public_id

        result = cloudinary.uploader.upload(str(path), **upload_opts)
        return result["secure_url"]

    # Local fallback
    try:
        return str(path.relative_to(config.UPLOADS_DIR))
    except ValueError:
        return str(path)


def delete_asset(path_or_url: str | None):
    """Delete an asset from Cloudinary or local disk."""
    if not path_or_url:
        return

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        if is_cloud_storage_enabled():
            import cloudinary.uploader

            try:
                # Cloudinary URLs: .../upload/v1234/<folder>/<public_id>.<ext>
                parts = path_or_url.split("/upload/")
                if len(parts) > 1:
                    public_part = parts[1]
                    if public_part.startswith("v") and "/" in public_part:
                        public_part = public_part.split("/", 1)[1]
                    public_id = public_part.rsplit(".", 1)[0]
                    cloudinary.uploader.destroy(public_id)
            except Exception as e:
                logger.warning("Failed to delete Cloudinary asset %s: %s", path_or_url, e)
    else:
        local_path = config.UPLOADS_DIR / path_or_url
        local_path.unlink(missing_ok=True)
