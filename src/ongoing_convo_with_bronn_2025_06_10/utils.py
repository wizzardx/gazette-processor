import os
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pdfplumber
from typeguard import typechecked

# Add the project root to the path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from icecream import ic

from validation_helpers import StrictBaseModel

from .cached_llm import CachedLLM


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


# Note: List of all of the abbreviations can be found in the footer of the docs
#       that Bronnwyn gave me


class ScanInfo(StrictBaseModel):
    plum_string: str


@typechecked
def load_or_scan_pdf_text(p: Path) -> ScanInfo:
    # Extract text using pdfplumber (first 5 pages by default)
    plum_text_pages = []
    with pdfplumber.open(p) as pdf:
        # Get up to first 5 pages
        pages_to_read = min(5, len(pdf.pages))
        for i in range(pages_to_read):
            page = pdf.pages[i]
            text = page.extract_text()
            if text:
                plum_text_pages.append(text)

    plum_string = "\n".join(plum_text_pages)

    # Ensure plum_string is not empty (StrictBaseModel requires min length 1)
    if not plum_string:
        plum_string = "[No plumber text extracted]"  # Placeholder for empty content

    return ScanInfo(plum_string=plum_string)


GG_DIR = Path(
    "/home/david/dev/misc/bronnwyn-stuff/bulletin-generator-rnd/files_from_bronnwyn/2025-05-28/David Bulletin/Source GGs/2025/"
)

#
# class MultipleMatchesFound(ValueError):
#     pass


@typechecked
def parse_gg_filename(filename: str) -> Optional[dict[str, Any]]:
    """
    Parse filename with pattern: gg{number}_{date}.pdf

    Returns:
        dict with 'gg_number' and 'publish_date' keys if pattern matches
        None if pattern doesn't match
    """
    # Pattern: gg followed by digits, underscore, date, .pdf
    pattern = r"^gg(\d+)_(\d{1,2}[A-Za-z]{3}\d{4})\.pdf$"

    match = re.match(pattern, filename)

    if match:
        gg_number = int(match.group(1))
        date_string = match.group(2)

        try:
            # Parse the date (e.g., "23May2025")
            publish_date = datetime.strptime(date_string, "%d%b%Y")

            return {"gg_number": gg_number, "publish_date": publish_date}
        except ValueError:
            # Invalid date format
            return None
    else:
        return None


@typechecked
class GgPdfs:
    def __init__(self) -> None:
        self._path: Optional[Path] = None
        self._gg_number: Optional[int] = None
        self._publish_date: Optional[datetime] = None

    def path(self) -> Path:
        assert self._path is not None
        return self._path

    def add_path(self, p: Path) -> None:
        parsed = parse_gg_filename(p.name)
        if parsed is not None:
            assert self._path is None
            self._path = p
            self._gg_number = parsed["gg_number"]
            self._publish_date = parsed["publish_date"]
        else:
            assert 0

    # assert 0
    # if result is not None:
    #     assert 0
    #     raise MultipleMatchesFound(f"Found multiple files containing gg number {gg_number}")
    # result = p
    # assertj 0
    #


@typechecked
def locate_gg_pdf_by_number(gg_number: int) -> GgPdfs:
    result = GgPdfs()
    gg_s = str(gg_number)
    for p in GG_DIR.iterdir():
        if gg_s in p.name:
            result.add_path(p)
    return result


@typechecked
def get_notice_for_gg_num(
    gg_number: int, notice_number: int, cached_llm: "CachedLLM"
) -> Notice:
    pdf_info = locate_gg_pdf_by_number(gg_number)
    p = pdf_info.path()
    return get_notice_for_gg(
        p=p, gg_number=gg_number, notice_number=notice_number, cached_llm=cached_llm
    )


@typechecked
def looks_like_a_year_string(s: str) -> bool:
    if not s.isdigit():
        return False
    if len(s) != 4:
        return False
    year = int(s)
    return 1900 <= year <= 2100


@typechecked
def attempt_to_get_pdf_page_num(pdf_gg_num: int, page_text_lower: str) -> int:
    # ic(locals())
    # eg:
    #
    # ic| locals(): {'TypeCheckMemo': <class 'typeguard.TypeCheckMemo'>,
    #                'check_argument_types': <function check_argument_types at 0x7fbd05870900>,
    #                'check_return_type': <function check_return_type at 0x7fbd058709a0>,
    #                'memo': <typeguard.TypeCheckMemo object at 0x7fbbdd627140>,
    #                'page_text_lower': 'staatskoerant; 23 mei-2025 no; 52726 3 government notices '
    #                                   'goewermentskennisgewings department of transport no. 6220 '
    #                                   '23 2025 draft comprehensive civil aviation policy the '
    #                                   'comments: interested persons are   requested to   submit '
    #                                   'written   comments in connection with-the draft '
    #                                   'comprehensive civil aviation policy within 30.days from '
    #                                   'the date of publication of this notice in the government '
    #                                   'gazette. all comments should be posted or emailed to the '
    #                                   'director- general of the department-of transport for the '
    #                                   'attention-of ms. johannah sekele as follows: department '
    #                                   'of transport private bag x 193 pretoria 0001 email: '
    #                                   'sekelej@dot_govza and tholot@dotgovza tel: 012 309 3760 '
    #                                   'may',
    #                'pdf_gg_num': 52726}
    # Traceback (most recent call last):
    page_split = page_text_lower.split()

    # We expect the word at index 4 to match the GG number:
    assert page_split[4] == str(pdf_gg_num)

    # And assuming it does, then in theory we have our page number next:
    return int(page_split[5])


class Act(StrictBaseModel):
    whom: str
    year: int
    number: int


@typechecked
def decode_complex_pdf_type_minor(scan_info: ScanInfo) -> Act:
    # Over here, we work with types of eg:
    # - ROAD ACCIDENT FUND ACT 56 OF 1996
    # - SKILLS DEVELOPMENT ACT 97 OF 1998
    # - COMPETITION ACT 89 OF 1998
    # - Currency and Exchanges-Act; 1933 (Act No: 9 of 1933)
    # https://claude.ai/chat/e5658a66-f818-46a3-a6fb-af63a4c7968c

    """
    Extract act information from legal text.

    Args:
        text (str): The legal text to parse

    Returns:
        Act: Act object containing 'whom', 'year', and 'number'

    Raises:
        ValueError: If no act information is found in the text
    """
    text = scan_info.plum_string

    # Pattern to match acts in the format: "NAME Act (NUMBER/YEAR)"
    pattern = r"([A-Za-z\s\-']+?)\s+Act\s+\((\d+)/(\d{4})\)"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        whom = match.group(1).strip()
        number = int(match.group(2))
        year = int(match.group(3))

        return Act(whom=whom, year=year, number=number)
    else:
        # Pattern for format: "NAME-Act; YEAR (Act No: NUMBER of YEAR)"
        pattern_semicolon = (
            r"([A-Za-z\s\-']+?)-Act;\s+(\d{4})\s+\(Act\s+No:?\s+(\d+)\s+of\s+\d{4}\)"
        )
        match_semicolon = re.search(pattern_semicolon, text, re.IGNORECASE)

        if match_semicolon:
            whom = match_semicolon.group(1).strip()
            year = int(match_semicolon.group(2))
            number = int(match_semicolon.group(3))

            return Act(whom=whom, year=year, number=number)
        else:
            # Fallback pattern for the older format: "NAME ACT, YEAR (ACT NO: NUMBER OF YEAR)"
            pattern_old = r"([A-Z'][A-Z\s']+?)\s+ACT,?\s+(\d{4})\s+\(ACT\s+NO:?\s+(\d+)\s+OF\s+\d{4}\)"
            match_old = re.search(pattern_old, text, re.IGNORECASE)

            if match_old:
                whom = match_old.group(1).strip()
                year = int(match_old.group(2))
                number = int(match_old.group(3))

                return Act(whom=whom, year=year, number=number)
            else:
                # Special cases here. We need the plumbum line to be joined by
                # spaces for this one, rather than newlines
                s = scan_info.plum_string.replace("\n", " ")
                if (
                    "with limited authority for the purpose of Exchange Control Regulations"
                    in s
                ):
                    return Act(
                        whom="Currency and Exchanges",
                        number=9,
                        year=1933,
                    )
                else:
                    print("```")
                    print(s)
                    print("```")
                    raise ValueError("No act information found in the provided text")


@typechecked
def looks_like_pdf_gen_n_num(n: int) -> bool:
    return 2000 <= n <= 9000


@typechecked
def looks_like_gg_num(n: int) -> bool:
    return 30000 <= n <= 90000


@typechecked
def looks_like_pdf_page_num(n: int) -> bool:
    return 1 <= n <= 100


def detect_major_type_from_notice_number(pdf_gen_n_num: int) -> MajorType:
    if 2000 < pdf_gen_n_num < 3000:
        return MajorType.BOARD_NOTICE
    if 3000 < pdf_gen_n_num < 4000:
        return MajorType.GENERAL_NOTICE
    elif 6000 < pdf_gen_n_num < 7000:
        return MajorType.GOVERNMENT_NOTICE
    else:
        raise ValueError(f"Unknown major type for notice number: {pdf_gen_n_num}")
    # Note: List of all of the abbreviations can be found in the footer of the docs
    #       that Bronnwyn gave me


@typechecked
def detect_pdf_year_num(scan_info: ScanInfo) -> int:
    text = scan_info.plum_string

    # Find all 4-digit numbers using word boundaries
    pattern = r"\b\d{4}\b"
    matches = re.findall(pattern, text)

    # Check each match to see if it's in the valid year range
    for match in matches:
        year = int(match)
        if 2000 <= year <= 3000:
            return year

    # Raise exception if no valid year found
    raise ValueError("No 4-digit year between 2000 and 3000 found in the text")


@typechecked
def detect_gg_num(text: str) -> int:
    # Find all 5-digit numbers starting with 5 using word boundaries
    pattern = r"\b5\d{4}\b"
    matches = re.findall(pattern, text)

    # Return the first match if found
    if matches:
        return int(matches[0])

    # Raise exception if no valid GG number found
    raise ValueError("No 5-digit number starting with 5 found in the text")


#
# @typechecked
# def detect_vol_num(text: str) -> int:
#     """
#     Extracts the volume number from a Government Gazette text.
#
#     Args:
#         text (str): The gazette text to search
#
#     Returns:
#         int: The volume number
#
#     Raises:
#         ValueError: If no volume number is found in the expected format
#     """
#     # Pattern to match "Vol." followed by whitespace and capture the digits
#     pattern = r'Vol\.\s+(\d+)'
#
#     match = re.search(pattern, text)
#
#     if match:
#         return int(match.group(1))
#     else:
#         raise ValueError("Volume number not found in the expected format 'Vol. XXX'")


@typechecked
def detect_monthday_num(text: str) -> int:
    """
    Extracts the day number from a Government Gazette string.

    Args:
        text (str): The input text containing the gazette information

    Returns:
        int: The day number

    Raises:
        ValueError: If no day number is found in the expected format
    """
    # Look for pattern "Vol." or "Vol:" followed by volume number, then day number, then year
    # Pattern: Vol[.:] [volume] [day] [year]
    pattern = r"Vol[.:]\s*\d+\s+(\d{1,2})\s+\d{4}"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        day = int(match.group(1))
        # Basic validation that it's a reasonable day number
        if 1 <= day <= 31:
            return day
        else:
            raise ValueError(f"Invalid day number: {day}. Must be between 1 and 31.")
    else:
        raise ValueError(
            "Day number not found in the expected format 'Vol. [volume] [day] [year]'"
        )


@typechecked
def detect_year_num(text: str) -> int:
    """
    Extracts the year number from a Government Gazette string.

    Args:
        text (str): The input text containing the gazette information

    Returns:
        int: The year number

    Raises:
        ValueError: If no year number is found in the expected format
    """
    # Look for pattern "Vol." or "Vol:" followed by volume number, day number, then year
    # Pattern: Vol[.:] [volume] [day] [year]
    pattern = r"Vol[.:]\s*\d+\s+\d{1,2}\s+(\d{4})"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        year = int(match.group(1))
        # Basic validation that it's a reasonable year (assuming modern gazettes)
        if 1900 <= year <= 2100:
            return year
        else:
            raise ValueError(
                f"Invalid year number: {year}. Must be between 1900 and 2100."
            )
    else:
        raise ValueError(
            "Year number not found in the expected format 'Vol. [volume] [day] [year]'"
        )


@typechecked
def detect_issn_num(text: str) -> str:
    """
    Extracts the ISSN from a Government Gazette string.

    Args:
        text (str): The input text containing the gazette information

    Returns:
        str: The ISSN in format ####-####

    Raises:
        ValueError: If no ISSN is found in the expected format
    """
    # Look for pattern "ISSN" followed by optional whitespace and the ISSN number
    # ISSN format is typically ####-#### (4 digits, hyphen, 4 digits)
    pattern = r"ISSN\s+(\d{4}-\d{4})"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        issn = match.group(1)
        return issn
    else:
        raise ValueError("ISSN not found in the expected format 'ISSN ####-####'")


@typechecked
def detect_monthday_en_str(text: str) -> str:
    """
    Extracts the English month name from a Government Gazette string.

    Args:
        text (str): The input text containing the gazette information

    Returns:
        str: The month name (e.g., "May", "January", etc.)

    Raises:
        ValueError: If no valid English month name is found
    """
    # List of valid English month names
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    # Create pattern that matches any of the month names (case-insensitive)
    # Look for month names that appear as standalone words
    month_pattern = r"\b(" + "|".join(months) + r")\b"

    match = re.search(month_pattern, text, re.IGNORECASE)

    if match:
        # Return the month with proper capitalization
        month = match.group(1)
        return month.capitalize()
    else:
        raise ValueError("No valid English month name found in the text")


@typechecked
def detect_page_number(text: str) -> int:
    """
    Extracts the page number from a Government Gazette string.
    The page number appears immediately after the 5-digit gazette number.

    Args:
        text (str): The input text containing the gazette information

    Returns:
        int: The page number

    Raises:
        ValueError: If no page number is found in the expected format
    """
    # Look for pattern "No." or "No:" or "No," followed by 5-digit number, then the page number
    # Pattern: No[.,:] [5-digit-number] [page-number]
    pattern1 = r"No[.,:]\s*(\d{5})\s+(\d+)"

    # Alternative pattern: underscore followed by 5-digit number and page number
    # Pattern: _ [5-digit-number] [page-number]
    pattern2 = r"_\s*(\d{5})\s+(\d+)"

    # Try first pattern
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        page_number = int(match.group(2))  # Second group is the page number
        # Basic validation that it's a reasonable page number
        if page_number > 0:
            return page_number
        else:
            raise ValueError(
                f"Invalid page number: {page_number}. Must be greater than 0."
            )

    # Try second pattern
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        page_number = int(match.group(2))  # Second group is the page number
        # Basic validation that it's a reasonable page number
        if page_number > 0:
            return page_number
        else:
            raise ValueError(
                f"Invalid page number: {page_number}. Must be greater than 0."
            )

    # If neither pattern matches
    raise ValueError(
        "Page number not found in the expected format 'No. [5-digit-number] [page-number]' or '_ [5-digit-number] [page-number]'"
    )


@typechecked
def get_notice_for_gg(
    p: Path, gg_number: int, notice_number: int, cached_llm: CachedLLM
) -> Notice:
    # Grab all text from the PDF file:
    ic(p)
    scan_info = load_or_scan_pdf_text(p)
    text = scan_info.plum_string

    # Sometimes this is a type of GG that lists

    # print("```")
    # print(text)
    # print("```")
    # ic(full_text)

    #     # Find the header text that contains volume and date information
    #     header_marker = "Government Gazette"
    #     header_start = full_text.find(header_marker)
    #     if header_start == -1:
    #         raise AssertionError("Could not find header marker in PDF text")
    #
    #     # Extract the header line
    #     header_end = full_text.find("\n", header_start)
    #     if header_end == -1:
    #         header_text = full_text[header_start:]
    #     else:
    #         header_text = full_text[header_start:header_end]
    #
    #     # Split the header text for parsing
    #     header_split = header_text.split()
    #
    #     ic()

    # ic(full_text)

    # @typechecked
    # def s(i: int) -> str:
    #     return header_split[i]
    #
    # @typechecked
    # def i(i: int) -> int:
    #     return int(s(i))

    # # pdf_vol_num = s(5)
    # pdf_vol_num = detect_vol_num(text)

    # pdf_monthday_num = i(6)
    pdf_monthday_num = detect_monthday_num(text)

    # pdf_year_num = detect_pdf_year_num(scan_info)  # i(7)
    pdf_year_num = detect_year_num(text)

    # pdf_gg_num = detect_gg_num(scan_info) # i(9)
    # pdf_gg_num = detect_gg_num(text)

    # # pdf_monthname_afr_str = s(10)
    # pdf_monthname_afr_str = detect_monthday_afr_str(text)

    # pdf_issn_num: Optional[str] = s(12)
    pdf_issn_num = detect_issn_num(text)

    # Sometimes the word "Government" appears instead of the ISSN number in the
    # scanned text. What this means is that the OCR'd text did not include the
    # ISSN.
    # if pdf_issn_num == "Government":
    #     pdf_issn_num = None

    # # pdf_monthname_en_str = s(-1)
    pdf_monthname_en_str = detect_monthday_en_str(text)

    #
    # # Find the "Contents" section in the full text
    # contents_marker = "Contents"
    # contents_start = full_text.find(contents_marker)
    # assert contents_start != -1, "Could not find Contents section"
    #
    # # Extract text after "Contents" to look for Gen number and page info
    # contents_text = full_text[contents_start:]
    # contents_split = contents_text.split()
    # # ic(contents_split)
    #
    # # Parse the contents section to find Gen number and page info
    # pdf_gen_n_num = None
    # gg_num_seen = False
    # pdf_page_num = None
    #
    # for idx, word in enumerate(contents_split):
    #     # Skip the first occurrence of "Contents" since we already found it
    #     if idx == 0 and word == "Contents":
    #         continue
    #
    #     # ic(word)
    #     if word.isdigit():
    #         int_word = int(word)
    #         if pdf_gen_n_num is None and looks_like_pdf_gen_n_num(int_word):
    #             pdf_gen_n_num = int_word
    #
    #         if gg_num_seen is False and looks_like_gg_num(int_word):
    #             gg_num_seen = True
    #
    #         if pdf_page_num is None and looks_like_pdf_page_num(int_word):
    #             pdf_page_num = int_word
    #
    # # Determine the major type by checking the Notice Number
    # if pdf_gen_n_num is None:
    #     raise ValueError("Unable to determine a Notice Number")
    pdf_type_major = detect_major_type_from_notice_number(notice_number)

    # Determine the minor type by searching the full text
    full_text_lower = text.lower()
    if "department of sports, arts and culture" in full_text_lower:
        pdf_type_minor = "Department of Sports, Arts and Culture"
    elif "national astro-tourism" in full_text_lower:
        pdf_type_minor = "Department of Tourism"
    elif "department of transport" in full_text_lower:
        pdf_type_minor = "Department of Transport"
    elif "authority for the purpose of exchange control" in full_text_lower:
        pdf_type_minor = "CURRENCY AND EXCHANGES ACT 9 OF 1933"
    else:
        # Over here, we work with types of eg:
        # - ROAD ACCIDENT FUND ACT 56 OF 1996
        # - SKILLS DEVELOPMENT ACT 97 OF 1998
        # - COMPETITION ACT 89 OF 1998
        act = decode_complex_pdf_type_minor(scan_info)
        pdf_type_minor = f"{act.whom} ACT {act.number} of {act.year}"
    #
    # # Extract the notice description text
    # # Find the gen_n_num in the contents section and get text after it
    # gen_n_num_seen = False
    # words_to_use = []
    #
    # # Look for the gen number in the contents text and extract description after it
    # for word in contents_split:
    #     if word == str(pdf_gen_n_num):
    #         gen_n_num_seen = True
    #     elif gen_n_num_seen:
    #         if word == "_":
    #             break
    #         else:
    #             words_to_use.append(word)
    #
    # pdf_text_content = " ".join(words_to_use)
    # # If we don't have the page number yet, try to find it in the full text
    # if pdf_page_num is None:
    #     # Look for pattern like "STAATSKOERANT; 23 MEI-2025 No; 52726 3"
    #     full_text_lower = full_text.lower()
    #     pdf_page_num = attempt_to_get_pdf_page_num(
    #         pdf_gg_num=pdf_gg_num, page_text_lower=full_text_lower
    #     )
    #
    # # Ensure all required fields are not None
    # if pdf_gen_n_num is None:
    #     # ic(full_text[:1000])
    #     raise ValueError("Could not find gen_n_num in PDF")
    # if pdf_page_num is None:
    #     # ic(full_text[:1000])
    #     raise ValueError("Could not find page number in PDF")
    #
    # # If we found the page number, but it was a none-3 value, then for now we
    # # assume that the scan was't reliable enough, and we set the value to None
    # # to indicate a bad scan
    # if pdf_page_num != 3:
    #     print(f"Detected page number {pdf_page_num}, assuming it was a bad OCR.")
    #     pdf_page_num = None
    #
    # # Check that auto-detectged gg number and notice number match the ones that
    # # were passed into the function
    # if pdf_gg_num != gg_number:
    #     print(
    #         f"Warning - detected GG number {gg_number}, but expected {pdf_gg_num}"
    #     )
    #     pdf_gg_num = gg_number
    #
    # if pdf_gen_n_num != notice_number:
    #     print(
    #         f"Warning - detected notice number {pdf_gen_n_num}, but expected {notice_number}"
    #     )
    #     pdf_gen_n_num = notice_number

    pdf_page_num = detect_page_number(text)
    pdf_text = cached_llm.summarize(text)

    print("```")
    print(text)
    print("```")

    notice = Notice(
        gen_n_num=notice_number,
        gg_num=gg_number,
        monthday_num=pdf_monthday_num,
        month_name=pdf_monthname_en_str,
        year=pdf_year_num,
        page=pdf_page_num,
        issn_num=pdf_issn_num,
        type_major=pdf_type_major,
        type_minor=pdf_type_minor,
        text=pdf_text,
    )
    # ic(notice)
    return notice
