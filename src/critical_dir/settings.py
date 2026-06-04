from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn
from pathlib import Path

class Settings(BaseSettings):
    pg_dsn: PostgresDsn
    datatable: str = 'criticalmaps_data'

    img_dir: Path
    api_downloader_json_outdir: Path

    model_config = SettingsConfigDict(
        env_file='.env',
        # ?add env_file_encoding='utf-8'
        env_prefix='CRITICAL_DIR_'
    )

# import this into your other files
settings = Settings()
