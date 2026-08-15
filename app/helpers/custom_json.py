import json
from dataclasses import asdict, fields, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import Any
from uuid import UUID

import isodate
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return isodate.datetime_isoformat(obj)

        elif isinstance(obj, date):
            return isodate.date_isoformat(obj)

        elif isinstance(obj, time):
            return isodate.time_isoformat(obj)

        elif isinstance(obj, timedelta):
            return isodate.duration_isoformat(obj)

        elif isinstance(obj, Decimal):
            return float(obj)

        elif isinstance(obj, set):
            return list(obj)

        elif isinstance(obj, BaseModel):
            return obj.model_dump()

        elif isinstance(obj, Enum):
            return obj.value

        elif is_dataclass(obj) and not isinstance(obj, type):
            return {field.name: self.default(getattr(obj, field.name)) for field in fields(obj)}

        elif isinstance(obj, UUID):
            return str(obj)

        elif isinstance(obj, bytes):
            return obj.decode()

        elif isinstance(obj, dict):
            return {key: self.default(value) for key, value in obj.items()}

        elif isinstance(obj, list):
            return [self.default(value) for value in obj]

        elif isinstance(obj, (int, str, float, bool)):
            return obj

        elif isinstance(obj, NoneType):
            return "null"

        return json.JSONEncoder.default(self, obj)


class CustomJSONResponse(JSONResponse):
    """Класс ответа в формате JSON"""

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(",", ":"),
            cls=CustomJsonEncoder,
        ).encode("utf-8")


def custom_json_serializer(obj):
    return json.dumps(obj, cls=CustomJsonEncoder)


def dumps(obj, *args, **kwargs):
    if kwargs.get("cls") is None:
        kwargs["cls"] = CustomJsonEncoder

    return json.dumps(obj, *args, **kwargs)


def loads(obj, *args, **kwargs):
    return json.loads(obj, *args, **kwargs)
