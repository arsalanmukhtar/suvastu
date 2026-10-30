import os

DB_URL = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+psycopg://", 1)
AOI_BBOX = [float(v) for v in os.environ.get("AOI_BBOX", "72.05,34.60,72.95,35.75").split(",")]
AOI_WKT = (
    f"POLYGON(({AOI_BBOX[0]} {AOI_BBOX[1]},{AOI_BBOX[2]} {AOI_BBOX[1]},"
    f"{AOI_BBOX[2]} {AOI_BBOX[3]},{AOI_BBOX[0]} {AOI_BBOX[3]},{AOI_BBOX[0]} {AOI_BBOX[1]}))"
)
EARTHDATA_USERNAME = os.environ.get("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.environ.get("EARTHDATA_PASSWORD")
EARTHDATA_TOKEN = os.environ.get("EARTHDATA_TOKEN")
CDSE_USERNAME = os.environ.get("CDSE_USERNAME")
CDSE_PASSWORD = os.environ.get("CDSE_PASSWORD")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
