from enum import Enum
from typing import Optional

from .validation_helpers import StrictBaseModel


class Notice(StrictBaseModel):
    gen_n_num: int
    gg_num: int
    monthday_num: int
    month_name: str
    year: int
    page: Optional[int]
    issn_num: Optional[str]
    type_major: "MajorType"
    type_minor: str
    text: str


class MajorType(Enum):
    BOARD_NOTICE = "BOARD_NOTICE"
    GENERAL_NOTICE = "GENERAL_NOTICE"
    GOVERNMENT_NOTICE = "GOVERNMENT_NOTICE"
    PROCLAMATION = "PROCLAMATION"


class Act(StrictBaseModel):
    whom: str
    year: Optional[int]
    number: Optional[int]
