from typing import Any

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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return self.model_dump(include=set(FileObject.model_fields)) == other
        if isinstance(other, FileObjectRequest):
            return (
                self.protocol == other.protocol
                and self.server == other.server
                and self.bucket == other.bucket
                and self.key == other.key
            )
        return super().__eq__(other)


class FileObjectRequest(FileObject):
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
            if not isinstance(default, StorageDefault):
                default = StorageDefault.model_validate(default)
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

    @classmethod
    def from_file_object(cls, file_object: FileObject | dict[str, Any]) -> "FileObjectRequest":
        """Populate the request from a FileObject or dict."""
        if isinstance(file_object, FileObject):
            file_object = file_object.model_dump()
        location = {key: file_object[key] for key in FileObject.model_fields}
        location["key"] = f"/{location['key'].lstrip('/')}"
        return cls.model_validate(location)

    @property
    def complete(self) -> bool:
        """Check if the file object has all required fields filled."""
        return all([self.protocol, self.bucket, self.key, self.expiration])


class FileObjectResponse(FileObject):
    url: str = Field(..., description="Presigned URL to upload or download the file.")
    expiration: int = Field(..., description="Expiration time in seconds for the presigned URL.")

    def to_file_object(self) -> FileObject:
        """Return a FileObject representation of this response."""
        return FileObject(
            protocol=self.protocol,
            server=self.server,
            bucket=self.bucket,
            key=self.key,
        )

    def dump_file_object(self) -> dict[str, Any]:
        """Return a dict of the FileObject representation of this response."""
        return self.to_file_object().model_dump()


class StorageDefault(TEMDBModel):
    protocol: StorageProtocol | None = Field(None, description="Default storage protocol for the system.")
    server: str | None = Field(None, description="Default server address.")
    bucket: str | None = Field(None, description="Default bucket")
    key_prefix: str | None = Field(None, description="Default key prefix")
    expiration: int | None = Field(None, description="Default expiration time in seconds for presigned URLs.")
