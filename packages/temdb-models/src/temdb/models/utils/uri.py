from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer
from smart_open import open


class URIObject:
    def __init__(self, uri):
        self._uri = uri

    def open(self, *args, **kwargs):
        return open(self.uri, *args, **kwargs)

    @property
    def uri(self):
        return self._uri

    @staticmethod
    def serialize(uri_object):
        return uri_object._uri

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
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


URI = Annotated[URIObject, PlainSerializer(URIObject.serialize), BeforeValidator(URIObject.validate)]
