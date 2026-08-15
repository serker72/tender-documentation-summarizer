from os import getcwd
from os.path import join

from .custom_dict import get_dict_from_toml_file


def get_project_info() -> dict:
    """Получение информации о проекте"""
    return get_dict_from_toml_file(
        join(getcwd(), "pyproject.toml"),
        {"project.name": "name", "project.description": "description", "project.version": "version"},
    )
