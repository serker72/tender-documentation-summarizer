from contextlib import suppress
from functools import reduce
from operator import getitem
from pathlib import Path
from typing import Any

from tomlkit_extras import load_toml_file


def get_dict_item_by_path(d: dict, keys: list[str]) -> Any | None:
    """Получение элемента вложенного словаря по списку ключей"""
    with suppress(Exception):
        return reduce(getitem, keys, d)

    return None


def set_dict_item_by_path(d: dict, keys: list[str], value: Any):
    """Установка значения элемента вложенного словаря по списку ключей"""
    for index in range(1, len(keys)):
        sub_item = get_dict_item_by_path(d, keys[:index])
        if not isinstance(sub_item, dict):
            get_dict_item_by_path(d, keys[:index][:-1])[keys[:index][-1]] = {}

    get_dict_item_by_path(d, keys[:-1])[keys[-1]] = value


def get_dict_from_toml_file(file_name: str | Path, keys: list[str] | dict[str, str] | None = None) -> dict:
    """
    Получение словаря из файла TOML с опционально ограниченным списком ключей.

    Опциональный параметр `keys` может содержать:
    - список получаемых ключей - ["key1", "key2.key3"]
    - словарь получаемых ключей - {"in_key1": "out_key1", "in_key2.in_key3": "out_key2.out_key3"}
    """
    toml_doc = load_toml_file(file_name)
    toml_dict = toml_doc.unwrap()

    if keys is None or len(keys) == 0:
        return toml_dict

    keys = {key: key for key in keys} if not isinstance(keys, dict) else keys

    data = {}
    for in_key, out_key in keys.items():
        set_dict_item_by_path(data, out_key.split("."), get_dict_item_by_path(toml_dict, in_key.split(".")))

    return data
