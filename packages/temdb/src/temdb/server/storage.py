import logging
from abc import ABC, abstractmethod
from collections import OrderedDict

import boto3
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
            self._client = boto3.client("s3", endpoint_url=server)
        except ClientError as e:
            logger.error("Failed to create S3 client: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create S3 client: {str(e)}",
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
                detail=f"Failed to generate presigned URL for GET: {str(e)}",
            )
        return FileObjectResponse(
            url=presigned_url,
            expiration=expiration,
            **storage_location.model_dump(exclude={"expiration"}),
        )

    def put_url(self, storage_location: FileObjectRequest) -> FileObjectResponse:
        try:
            presigned_url = self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": storage_location.bucket,
                    "Key": storage_location.key,
                },
                ExpiresIn=storage_location.expiration or 3600,
            )
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to generate presigned URL for PUT: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL for PUT: {str(e)}",
            )
        return FileObjectResponse(
            url=presigned_url,
            expiration=storage_location.expiration or 3600,
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
                detail=f"Failed to delete object from S3: {str(e)}",
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

    def put_url(self, storage_location: FileObjectRequest) -> FileObjectResponse:
        client = self.get_client(storage_location.protocol, storage_location.server)
        return client.put_url(storage_location)

    def get_url(self, storage_location: FileObject, expiration=None) -> FileObjectResponse:
        client = self.get_client(storage_location.protocol, storage_location.server)
        return client.get_url(storage_location, expiration)

    def delete(self, storage_location: FileObject) -> None:
        client = self.get_client(storage_location.protocol, storage_location.server)
        return client.delete(storage_location)

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
        return storage_location
