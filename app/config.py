from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    api_prefix: str = "/v1"
    api_key: str = Field(..., description="Static API key for simple auth")
    cors_origins: str = "*"

    azure_openai_key: str = Field(..., alias="AZURE_OPENAI_KEY")
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_API_VERSION")
    azure_deployment_name: str = Field(..., alias="AZURE_DEPLOYMENT_NAME")

    azure_embedding_deployment: str = Field(..., alias="AZURE_EMBEDDING_DEPLOYMENT")

    qdrant_host: str = Field(default="127.0.0.1", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_collection: str = Field(default="memory", alias="QDRANT_COLLECTION")
    qdrant_distance: str = Field(default="COSINE", alias="QDRANT_DISTANCE")
    embedding_dim: int = Field(default=1536, alias="EMBEDDING_DIM")

    gcp_project_id: str = Field(..., alias="GCP_PROJECT_ID")
    firestore_collection: str = Field(default="conversations")
    max_context_messages: int = Field(default=12)
    
    # Configurable metric kinds for health analysis
    default_metric_kinds: list[str] = Field(
        default=["hr", "hrv", "steps", "sleep"], 
        alias="DEFAULT_METRIC_KINDS",
        description="Default metric kinds to analyze when not specified in request"
    )
    available_metric_kinds: list[str] = Field(
        default=["hr", "hrv", "steps", "sleep", "weight", "blood_pressure", "temperature", "glucose", "oxygen_saturation"],
        alias="AVAILABLE_METRIC_KINDS", 
        description="All available metric kinds that can be analyzed"
    )

    firestore_emulator_host: Optional[str] = Field(
        default=None, alias="FIRESTORE_EMULATOR_HOST"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
