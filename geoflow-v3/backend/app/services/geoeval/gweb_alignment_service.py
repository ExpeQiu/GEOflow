"""兼容导入：请改用 geoweb_alignment_service。"""

from app.services.geoeval.geoweb_alignment_service import (  # noqa: F401
    compute_geoweb_alignment,
    compute_gweb_alignment,
    fetch_geoweb_pages,
    fetch_gweb_pages,
)
