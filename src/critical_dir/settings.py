from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn
from pathlib import Path
from functools import cache

class Settings(BaseSettings):
    pg_dsn: PostgresDsn
    datatable: str = 'criticalmaps_data'

    img_dir: Path
    api_downloader_json_outdir: Path

    # controls privacy-friendly behavior of the API server (for example: do not expose exact geolocations of individual users)
    privacy_mode: bool = True

    test_mode: bool = False

    model_config = SettingsConfigDict(
        env_file='.env',
        # ?add env_file_encoding='utf-8'
        env_prefix='CRITICAL_DIR_'
    )

# Import this into your other files
# Note: using "@cache" decorator to prevent inconsistencies when the
# configuration data (on disk) changes during the runtime of the program.
@cache
def get_settings() -> Settings:
    return Settings()
