from typing import Any, Optional, Union

from PIL.Image import Image

def image_to_string(
    image: Union[Image, str],
    lang: Optional[str] = None,
    config: str = "",
    nice: int = 0,
    output_type: str = "string",
    timeout: int = 0,
) -> str: ...
def image_to_data(
    image: Union[Image, str],
    lang: Optional[str] = None,
    config: str = "",
    nice: int = 0,
    output_type: str = "dict",
    timeout: int = 0,
) -> dict[str, Any]: ...
def image_to_boxes(
    image: Union[Image, str],
    lang: Optional[str] = None,
    config: str = "",
    nice: int = 0,
    output_type: str = "string",
    timeout: int = 0,
) -> str: ...
def get_languages(config: str = "") -> list[str]: ...
