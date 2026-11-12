import asyncio
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

from temdb.models import FileObject, FileObjectRequest, FileObjectResponse, StorageProtocol

logger = logging.getLogger(__name__)


class StorageClient(ABC):
    @abstractmethod
    def get_url(self, storage_location: FileObject, expiration: int | None = None) -> FileObjectResponse:
        pass

    @abstractmethod
    def put_url(self, storage_location: FileObjectRequest) -> FileObjectResponse:
        pass

    @abstractmethod
    def delete(self, storage_location: FileObject) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class S3StorageClient(StorageClient):
    def __init__(self, server: str | None = None):
        try:
            self._client = boto3.client("s3", endpoint_url=server, config=Config(signature_version="s3v4"))
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to create S3 client: %s", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to create S3 client",
            )

    def close(self) -> None:
        self._client.close()

    def get_url(self, storage_location: FileObject, expiration: int | None = None) -> FileObjectResponse:
        expiration = expiration or 3600
        try:
            presigned_url = self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": storage_location.bucket,
                    "Key": storage_location.key,
                },
                ExpiresIn=expiration,
            )
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to generate presigned URL for GET: %s", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to generate presigned URL for GET",
            )
        try:
            metadata = self._client.head_object(
                Bucket=storage_location.bucket, Key=storage_location.key, ChecksumMode="ENABLED"
            )
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to retrieve object hash from S3: %s", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve object hash from S3",
            )
        hash = metadata.get("ChecksumSHA256")
        if not hash:
            logger.error(
                "ChecksumSHA256 not found in S3 object metadata for %s/%s",
                storage_location.bucket,
                storage_location.key,
            )
            raise HTTPException(
                status_code=500,
                detail="SHA 256 hash not in S3 object metadata",
            )
        return FileObjectResponse(
            url=presigned_url,
            expiration=expiration,
            **storage_location.model_dump(include=set(FileObject.model_fields)),
            hash=hash,
        )

    def put_url(self, storage_location: FileObjectRequest) -> FileObjectResponse:
        expiration = storage_location.expiration or 3600
        try:
            presigned_url = self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": storage_location.bucket,
                    "Key": storage_location.key,
                    "ChecksumSHA256": storage_location.hash,
                },
                ExpiresIn=expiration,
            )
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to generate presigned URL for PUT: %s", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to generate presigned URL for PUT",
            )
        return FileObjectResponse(
            url=presigned_url,
            expiration=expiration,
            **storage_location.model_dump(exclude={"expiration"}),
        )

    def delete(self, storage_location: FileObject) -> None:
        try:
            self._client.delete_object(
                Bucket=storage_location.bucket,
                Key=storage_location.key,
            )
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to delete object from S3: %s", e)
            raise HTTPException(
                status_code=500,
                detail="Failed to delete object from S3",
            )


class StorageClientManager:
    def __init__(self, max_clients: int = 5):
        if max_clients < 1:
            raise ValueError("max_clients must be at least 1")
        self.max_clients = max_clients
        self._clients = OrderedDict()

    def get_client(self, protocol, server):
        key = (protocol, server)
        if key in self._clients:
            self._clients.move_to_end(key)
            return self._clients[key]

        client = self._create_client(protocol, server)
        self._clients[key] = client

        while len(self._clients) > self.max_clients:
            _, evicted = self._clients.popitem(last=False)
            evicted.close()

        return client

    def _create_client(self, protocol, server):
        match protocol:
            case StorageProtocol.S3:
                return S3StorageClient(server)
            case StorageProtocol.GCS:
                raise HTTPException(
                    status_code=501,
                    detail="GCS storage protocol is not implemented yet.",
                )
            case _:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported storage protocol: {protocol}",
                )

    async def put_url(self, storage_location: FileObjectRequest) -> FileObjectResponse:
        client = self.get_client(storage_location.protocol, storage_location.server)
        return await asyncio.to_thread(client.put_url, storage_location)

    async def get_url(self, storage_location: FileObject, expiration=None) -> FileObjectResponse:
        client = self.get_client(storage_location.protocol, storage_location.server)
        return await asyncio.to_thread(client.get_url, storage_location, expiration)

    async def delete(self, storage_location: FileObject) -> None:
        client = self.get_client(storage_location.protocol, storage_location.server)
        await asyncio.to_thread(client.delete, storage_location)

    def close(self) -> None:
        for client in self._clients.values():
            client.close()
        self._clients.clear()

    @staticmethod
    def finalize(storage_location: FileObjectRequest) -> FileObjectRequest:
        if storage_location.protocol is None:
            raise HTTPException(
                status_code=400,
                detail="Storage protocol must be specified.",
            )
        if storage_location.bucket is None:
            raise HTTPException(
                status_code=400,
                detail="Storage bucket must be specified.",
            )
        if storage_location.key is None:
            raise HTTPException(
                status_code=400,
                detail="Storage key must be specified.",
            )
        storage_location.key = storage_location.key.lstrip("/")
        if not storage_location.key:
            raise HTTPException(
                status_code=400,
                detail="Storage key must not be empty.",
            )
        return storage_location

    @staticmethod
    def apply_file_object(
        storage_location: FileObjectRequest, file_object: FileObject | dict | None
    ) -> FileObjectRequest:
        if file_object is None:
            return storage_location
        if isinstance(file_object, dict):
            file_object = FileObject.model_validate(file_object)
        if storage_location.protocol is None:
            storage_location.protocol = file_object.protocol
            storage_location.server = file_object.server
        if storage_location.bucket is None:
            storage_location.bucket = file_object.bucket
        if storage_location.key is None:
            storage_location.key = f"/{file_object.key.lstrip('/')}"
        return storage_location
