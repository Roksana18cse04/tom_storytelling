#app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    openai_api_key: str
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    mongo_url: str
    
    # AWS S3 Configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    s3_bucket_name: str

    class Config:
        env_file= ".env"

settings= Settings()
