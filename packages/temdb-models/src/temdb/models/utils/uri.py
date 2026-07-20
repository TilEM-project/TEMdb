import logging
import os
import posixpath
from typing import Annotated

import boto3
import yaml
from pathlib_abc import JoinablePath, vfspath
from platformdirs import user_config_path
from pydantic import (
    BaseModel,
    BeforeValidator,
    PlainSerializer,
    ValidationError,
    WithJsonSchema,
    field_validator,
)
from smart_open import open, parse_uri

logger = logging.getLogger(__name__)


class _DataLocation(BaseModel):
    transport: str

    @property
    def transport_params(self):
        return None

    def match(self, **attrs):
        for attr, val in attrs.items():
            if val is not None and getattr(self, attr) is not None and getattr(self, attr) != val:
                return False
        return True


class _S3DataLocation(_DataLocation):
    host: str = None
    port: int = 443
    bucket: str = None
    region: str = "us-east-1"
    access_key_id: str = None
    secret_access_key: str = None
    use_ssl: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                use_ssl=self.use_ssl,
                endpoint_url=None
                if self.host is None
                else f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}",
            )
        return self._client

    @property
    def transport_params(self):
        self._get_client()
        return {
            "client": self._get_client(),
        }

    def match(self, bucket_id=None, host=None, port=None, region=None, **kwargs):
        return super().match(
            bucket=bucket_id,
            host=host,
            port=port,
            region=region,
        )


class _DataLocationConfig(BaseModel):
    data_locations: list[_DataLocation] = []

    @field_validator("data_locations", mode="before")
    @classmethod
    def infer_classes(cls, locations):
        for location in locations:
            match location["transport"]:
                case "s3":
                    yield _S3DataLocation.model_validate(location)
                case _:
                    yield _DataLocation.model_validate(location)

    def get_transport_params(self, **attrs):
        for location in self.data_locations:
            if location.match(**attrs):
                return location.transport_params
        return {}

    def add_data_location(self, **config):
        self.data_locations += self.infer_classes([config])


class _DataConfig(_DataLocationConfig):
    @classmethod
    def load(cls, path=None):
        def load(path):
            with open(path) as f:
                return cls.model_validate(yaml.safe_load(f))

        def try_load(path):
            try:
                return load(path)
            except (OSError, ValidationError) as e:
                logger.debug(f"Could not load config file from: {path}. Error:\n{e}")

        if path is None:
            config_dir = user_config_path("TEMdb", "TilEM")
            data = try_load(config_dir / "data_config.yaml")
            if data:
                return data
            data = try_load(config_dir / "data_config.yml")
            if data:
                return data
            return cls()
        else:
            return load(path)


data_config = _DataConfig.load()


class _classproperty(property):
    def __get__(self, _, owner):
        return self.fget(owner)


class URI(JoinablePath):
    data_config = data_config
    parser = posixpath

    @_classproperty
    def Type(cls):
        return Annotated[
            cls,
            PlainSerializer(cls.serialize),
            BeforeValidator(cls.validate),
            WithJsonSchema({"type": "string"}),
        ]

    def __init__(self, *pathsegments):
        if not pathsegments:
            self.uri = ""
            return

        normalized_segments = tuple(self._normalize_pathsegment(segment) for segment in pathsegments)
        if len(normalized_segments) == 1:
            self.uri = normalized_segments[0]
        else:
            self.uri = self.parser.join(*normalized_segments)

    @staticmethod
    def _normalize_pathsegment(segment):
        if isinstance(segment, URI):
            return segment.uri
        if isinstance(segment, JoinablePath):
            return vfspath(segment)
        if isinstance(segment, os.PathLike):
            return os.fspath(segment)
        if isinstance(segment, str):
            return segment
        raise TypeError(f"pathsegments should be strings or path-like objects, not {type(segment).__name__!r}")

    def __vfspath__(self):
        return self.uri

    def __fspath__(self):
        return self.uri

    def with_segments(self, *pathsegments):
        return type(self)(*pathsegments)

    def open(self, mode="r", transport_params=None, **kwargs):
        if transport_params is None:
            transport_params = self._transport_params
        return open(self.uri, mode=mode, transport_params=transport_params, **kwargs)

    @staticmethod
    def serialize(uri_object):
        return uri_object.uri

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
        elif isinstance(value, (JoinablePath, os.PathLike)):
            return cls(value)
        elif isinstance(value, str):
            return cls(value)
        else:
            raise ValueError(f"Must be either a string or an instance of {cls.__name__}.")

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.uri == other.uri
        elif isinstance(other, str):
            return self.uri == other
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.uri)

    def __str__(self):
        return self.uri

    def __repr__(self):
        return f"URI({self.uri})"

    @property
    def _transport_params(self):
        parsed = parse_uri(self.uri)
        return self.data_config.get_transport_params(**parsed._asdict())
