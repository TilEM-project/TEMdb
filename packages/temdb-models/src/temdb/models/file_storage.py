from pydantic import Field, model_validator

from .base import TEMDBModel
from .enums import StorageProtocol


class FileObject(TEMDBModel):
    protocol: StorageProtocol = Field(
        ..., description="Storage protocol used for the file, or None to use the default."
    )
    server: str = Field(..., description="Server address or None for protocol default.")
    bucket: str = Field(..., description="Bucket where the file is stored.")
    key: str = Field(..., description="Key to the file within the bucket.")


class FileObjectRequest(TEMDBModel):
    protocol: StorageProtocol | None = Field(
        None, description="Storage protocol used for the file, or None to use the default."
    )
    server: str | None = Field(None, description="Server address or None for protocol default.")
    bucket: str | None = Field(None, description="Bucket where the file is stored, or None to use the default.")
    key: str = Field(
        ..., description="Key to the file within the bucket. Use a leading slash to ignore the default key prefix."
    )
    expiration: int | None = Field(
        None, description="Expiration time in seconds for the presigned URL, or None to use the default."
    )

    @model_validator(mode="after")
    def validate_location(self) -> "FileObjectRequest":
        if self.server is not None and self.protocol is None:
            raise ValueError("If server is specified, protocol must also be specified.")
        if self.protocol is not None and self.bucket is None:
            raise ValueError("If protocol is specified, bucket must also be specified.")
        if self.bucket is not None and not self.key.startswith("/"):
            raise ValueError(
                "If bucket is specified, key must start with a leading slash to ignore the default key prefix."
            )
        return self

    def apply_defaults(self, *defaults: "StorageDefault") -> "FileObjectRequest":
        """Apply default storage settings to the request."""
        for default in defaults:
            if self.protocol is None:
                self.protocol = default.protocol
                self.server = default.server
            if self.bucket is None:
                self.bucket = default.bucket
            if self.key.startswith("/") and default.key_prefix is not None:
                self.key = f"{default.key_prefix.strip('/')}/{self.key.lstrip('/')}"
            if self.expiration is None:
                self.expiration = default.expiration
        return self


class FileObjectResponse(FileObject):
    url: str = Field(..., description="Presigned URL to upload or download the file.")
    expiration: int = Field(..., description="Expiration time in seconds for the presigned URL.")


class StorageDefault(TEMDBModel):
    protocol: StorageProtocol | None = Field(None, description="Default storage protocol for the system.")
    server: str | None = Field(None, description="Default server address.")
    bucket: str | None = Field(None, description="Default bucket")
    key_prefix: str | None = Field(None, description="Default key prefix")
    expiration: int | None = Field(None, description="Default expiration time in seconds for presigned URLs.")
