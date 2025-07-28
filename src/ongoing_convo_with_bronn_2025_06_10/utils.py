import csv
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Any, Optional

import pdfplumber
from pydantic import BaseModel
from typeguard import typechecked

# Add the project root to the path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from icecream import ic

from .prints import print1, print2

logger = logging.getLogger(__name__)

from .cached_llm import CachedLLM
from .common_types import Act, MajorType, Notice
from .pdf_parser_multi_leading_r_notice import (
    get_act_leading_r_from_multi_notice_pdf,
    get_notice_leading_r_from_multi_notice_pdf,
)
from .pdf_parser_multi_notice import get_notice_from_multi_notice_pdf
from .pdf_parser_single_notice import get_notice_from_single_notice_pdf

# Note: List of all of the abbreviations can be found in the footer of the docs
#       that Bronnwyn gave me


@typechecked
def load_or_scan_pdf_text(p: Path) -> tuple[str, list[str]]:
    # TODO: Rename function name "or scan" to "or ocr"
    # Create cache directory if it doesn't exist
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)

    # Calculate MD5 hash of the file contents
    with open(p, "rb") as f:
        file_hash = hashlib.md5(f.read()).hexdigest()

    # Create cache file path based on hash
    # TODO: Refactor Cache -related logic in other places, too.
    cache_file = cache_dir / f"{file_hash}.json"

    # Check if cached result exists
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
            return cached_data["text"], cached_data["pages"]

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

    # Save to cache using a temporary file for atomic writes
    cache_data = {"text": plum_string, "pages": plum_text_pages}
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=cache_dir, delete=False
    ) as tmp_file:
        json.dump(cache_data, tmp_file)
        tmp_path = Path(tmp_file.name)

    # Atomically move the temporary file to the final location
    tmp_path.replace(cache_file)

    return plum_string, plum_text_pages


# GG_DIR_X = Path(
#     "/hom, gg_dir: Pathe/david/dev/misc/bronnwyn-stuff/bulletin-generator-rnd/files_from_bronnwyn/2025-05-28/David Bulletin/Source GGs/2025/"
# )

#
# class MultipleMatchesFound(ValueError):
#     pass


@typechecked
def parse_gg_filename(filename: str) -> Optional[dict[str, Any]]:
    """
    Parse filename with pattern: gg{number}_{date}.pdf

    Supports both abbreviated (e.g., "23May2025") and full month names (e.g., "20February2025")

    Returns:
        dict with 'gg_number' and 'publish_date' keys if pattern matches
        None if pattern doesn't match
    """
    # Pattern: gg followed by digits, underscore, date, .pdf
    # Changed [A-Za-z]{3} to [A-Za-z]+ to allow variable-length month names
    pattern = r"^gg(\d+)_(\d{1,2}[A-Za-z]+\d{4})\.pdf$"

    match = re.match(pattern, filename)

    if match:
        gg_number = int(match.group(1))
        date_string = match.group(2)

        # Try parsing with full month name first, then abbreviated
        for date_format in ["%d%B%Y", "%d%b%Y"]:
            try:
                publish_date = datetime.strptime(date_string, date_format)
                return {"gg_number": gg_number, "publish_date": publish_date}
            except ValueError:
                continue

        # If neither format worked, return None
        return None
    else:
        return None


@typechecked
def locate_gg_pdf_by_number(gg_number: int, gg_dir: Path) -> Path:
    result = None
    gg_s = str(gg_number)
    for p in gg_dir.iterdir():
        if gg_s in p.name:
            return p
    raise ValueError(
        f"Could not find a PDF file with GG Number {gg_number} in directory {gg_dir}"
    )


@typechecked
def get_notice_for_gg_num(
    gg_number: int,
    notice_number: int,
    cached_llm: "CachedLLM",
    gg_dir: Path,
) -> Notice:
    p = locate_gg_pdf_by_number(gg_number, gg_dir=gg_dir)
    return get_notice_for_gg(
        p=p,
        gg_number=gg_number,
        notice_number=notice_number,
        cached_llm=cached_llm,
    )


def output_testing_bulletin(gg_dir: Path) -> None:
    cached_llm = CachedLLM()

    f = open("notices.csv")
    csvreader = csv.DictReader(f)
    row = next(csvreader)

    # We can comment out the below assignment during development to assist with
    # debugging.
    notice = get_notice_for_gg_num(
        gg_number=int(row["gazette_number"]),
        notice_number=int(row["notice_number"]),
        cached_llm=cached_llm,
        gg_dir=gg_dir,
    )

    if notice is None:
        logger.warning("The first Notice was disabled for debug purposes.")
        print1()

    print1("# **JUTA'S WEEKLY STATUTES BULLETIN**")

    print1()
    print1(
        "##### (Bulletin 21 of 2025 based on Gazettes received during the week 16 to 23 May 2025)"
    )
    print1()
    print1("## JUTA'S WEEKLY E-MAIL SERVICE")
    print1()

    # eg major: PROCLAMATIONS AND NOTICES
    # eg minor: Department of Sports, Arts and Culture:
    # /type_major, type_minor = get_notice_type(notice.gen_n_num)

    if notice is not None:
        print1(f"*ISSN {notice.issn_num}*")

    @typechecked
    def to_bb_header_str(t: MajorType) -> str:
        return {
            MajorType.GENERAL_NOTICE: "PROCLAMATIONS AND NOTICES",
            MajorType.BOARD_NOTICE: "BOARD NOTICE",
            MajorType.GOVERNMENT_NOTICE: "GOVERNMENT NOTICE",
            MajorType.PROCLAMATION: "PROCLAMATION",
        }[t]

        # Note: List of all of the abbreviations can be found in the footer of the docs
        #       that Bronnwyn gave me

    print1()
    # print("PROCLAMATIONS AND NOTICES")
    if notice is not None:
        header_str = to_bb_header_str(notice.type_major)
        print1(f"## **{header_str}**")
        print1()
        # print("Department of Sports, Arts and Culture:")
        print1(f"### **{notice.type_minor}**")
        print1()

    # print(f"Draft National Policy Framework for Heritage Memorialisation published for comment (GenN 3228 in GG 52724 of 23 May 2025) (p3)")

    @typechecked
    def get_notice_type_abbr(t: MajorType) -> str:
        # ic(t)
        return {
            MajorType.GENERAL_NOTICE: "GenN",
            MajorType.GOVERNMENT_NOTICE: "GN",
            MajorType.BOARD_NOTICE: "BN",
            MajorType.PROCLAMATION: "Proc",
        }[t]

        # Note: List of all of the abbreviations can be found in the footer of the docs
        #       that Bronnwyn gave me

    if notice is not None:
        notice_type_major_abbr = get_notice_type_abbr(notice.type_major)

        print1(
            f"{notice.text}\n\n({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"
        )

    print1()

    @typechecked
    def _compare_against_json_serialization(gg_number: int, notice: Notice) -> None:
        j = json.loads(notice.model_dump_json())

        # If a cached version of the json (keyed by gg number) exists in our cache
        # directory, then load and compare against that version, otherwise make
        # a new cache file to use next time
        cache_dir = Path("cache")
        cache_file = cache_dir / f"gg{gg_number}_notice.json"

        if cache_file.exists():
            # Load the cached version
            with open(cache_file, "r") as f:
                cached_notice = json.load(f)

            # Compare the current notice with the cached version
            if j != cached_notice:
                logger.warning(
                    f"Notice for GG {gg_number} has changed since last cache!"
                )
                logger.debug(f"Cached: {cached_notice}")
                logger.debug(f"Current: {j}")
                # assert 0
            else:
                logger.info(f"Notice for GG {gg_number} matches cached version.")
        else:
            # Create the cache file for next time
            cache_dir.mkdir(exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(j, f, indent=2)
            logger.info(f"Created cache file for GG {gg_number} at {cache_file}")

    @typechecked
    def print_notice_info(
        gg_number: int, notice_number: int, cached_llm: CachedLLM, gg_dir: Path
    ) -> tuple[str, str]:
        notice = get_notice_for_gg_num(
            gg_number=gg_number,
            notice_number=notice_number,
            cached_llm=cached_llm,
            gg_dir=gg_dir,
        )
        notice_type_major_abbr = get_notice_type_abbr(notice.type_major)
        # print("Department of Tourism:")

        # print("Department of Sports, Arts and Culture:")
        type_minor = notice.type_minor

        # Only bring the later ones to uppercase:
        if type_minor not in {"Department of Tourism", "Department of Transport"}:
            type_minor = type_minor.upper()

        print1(f"### **{type_minor}**")
        print1()

        part1 = f"{notice.text}"
        part2 = f"({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"

        # print("National Astro-Tourism Strategy published for implementation")\
        print1(f"{part1}\n\n{part2}")

        print1()

        # Next, compare the notice gainst a previous JSON serialization of the
        # record, if that exists.
        # _compare_against_json_serialization(gg_number=gg_number, notice=notice)
        return (type_minor, part2)

    def print_notice(notice_number: int, gg_number: int) -> tuple[str, str]:
        return print_notice_info(
            notice_number=notice_number,
            gg_number=gg_number,
            cached_llm=cached_llm,
            gg_dir=gg_dir,
        )

    #
    # # Department of Tourism
    # assert print_notice(3229, 52725) == (
    #     "Department of Tourism",
    #     "(GenN 3229 in GG 52725 of 23 May 2025) (p3)",
    # )
    #
    # # Department of Transport:
    # assert print_notice(6220, 52726) == (
    #     "Department of Transport",
    #     "(GN 6220 in GG 52726 of 23 May 2025) (p3)",
    # )
    #
    # # CURRENCY AND EXCHANGES ACT 9 OF 1933
    # assert print_notice(3197, 52695) == (
    #     "CURRENCY AND EXCHANGES ACT 9 OF 1933",
    #     "(GenN 3197 in GG 52695 of 16 May 2025) (p3)",
    # )
    #
    # # MAGISTRATES' COURTS ACT 32 OF 1944
    # assert print_notice(6219, 52723) == (
    #     "MAGISTRATES' COURTS ACT 32 OF 1944",
    #     "(GN 6219 in GG 52723 of 23 May 2025) (p3)",
    # )
    #
    # # SUBDIVISION OF AGRICULTURAL LAND ACT 70 OF 1970
    # assert print_notice(6214, 52712) == (
    #     "SUBDIVISION OF AGRICULTURAL LAND ACT 70 OF 1970",
    #     "(GN 6214 in GG 52712 of 23 May 2025) (p14)",
    # )
    #
    # # PHARMACY ACT 53 OF 1974
    # assert print_notice(787, 52709) == (
    #     "PHARMACY ACT 53 OF 1974",
    #     "(BN 787 in GG 52709 of 21 May 2025) (p3)",
    # )
    #
    # # COMPENSATION FOR OCCUPATIONAL INJURIES AND DISEASES ACT 130 OF 1993
    # assert print_notice(3200, 52699) == (
    #     "COMPENSATION FOR OCCUPATIONAL INJURIES AND DISEASES ACT 130 OF 1993",
    #     "(GenN 3200 in GG 52699 of 19 May 2025) (p3)",
    # )
    #
    # assert print_notice(3227, 52722) == (
    #     "COMPENSATION FOR OCCUPATIONAL INJURIES AND DISEASES ACT 130 OF 1993",
    #     "(GenN 3227 in GG 52722 of 23 May 2025) (p3)",
    # )
    #
    # # ROAD ACCIDENT FUND ACT 56 OF 1996
    # assert print_notice(786, 52691) == (
    #     "ROAD ACCIDENT FUND ACT 56 OF 1996",
    #     "(BN 786 in GG 52691 of 16 May 2025) (p205)",
    # )
    #
    # # SPECIAL INVESTIGATING UNITS AND SPECIAL TRIBUNALS ACT 74 OF 1996
    # assert print_notice(260, 52705) == (
    #     "SPECIAL INVESTIGATING UNITS AND SPECIAL TRIBUNALS ACT 74 OF 1996",
    #     "(Proc 260 in GG 52705 of 23 May 2025) (p24)",
    # )
    #
    # # And then a bunch of others over here:
    # MORE_NUMBERS = """
    #     6215  52712
    #     261   52720
    #
    #     3220  52712
    #     3221  52712
    #     3222  52712
    #
    #     6208  52698
    #
    #     6202  52691
    #
    #     3219  52712
    #
    #     783   52691
    #
    #     3194   52691
    #
    #     3199   52697
    #
    #     6213   52711
    #
    #     3218   52712
    #
    #     6212   52710
    #
    #     6217  52712
    #
    #     6216  52712
    #
    #     3201   52701
    #
    #     6210   52704
    #
    # """

    notices_with_technical_issues: list[tuple[int, int]] = []

    for item in csvreader:
        notice_num = int(item["notice_number"])
        gg_num = int(item["gazette_number"])

        try:
            print_notice(notice_num, gg_num)
        except Exception as e:
            logger.exception(
                f"There was a problem processing Notice {notice_num} in Government Gazette {gg_num}: {e!r}"
            )
            notices_with_technical_issues.append((notice_num, gg_num))

    print1()
    print1("ABBREVIATIONS:")
    print1(
        "GG (Government Gazette), GenN (General Notice), GN (Government Notice), BN (Board Notice), Proc (Proclamation), PG (Provincial Gazette), PN (Provincial Notice), PremN (Premier's Notice), ON (Official Notice), LAN (Local Authority Notice), MN (Municipal Notice)"
    )
    print1()
    print1("Compiled by Juta's Statutes Editors - © Juta and Company (Pty) Ltd")
    print1("PO BOX 24299 LANSDOWNE 7779 TEL:")
    print1("(021) 659 2300 E-MAIL:")
    print1("statutes@juta.co.za")
    print1()

    if notices_with_technical_issues:
        print1("## **NOTICES WITH TECHNICAL ISSUES**")
        print1()
        print1(
            f"NB: There were {len(notices_with_technical_issues)} Notices with technical issues in the Government Gazettes. Please check these manually."
        )
        print1()
        for notice_info in notices_with_technical_issues:
            print1(f"- Notice {notice_info[0]} of {notice_info[1]}")
            print1()
        print1()


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


class UnableToGetActInfo(ValueError):
    pass


##########


@typechecked
def decode_complex_pdf_type_minor(
    text: str, pages: list[str], notice_number: int
) -> Act:
    """
    Extract act information from legal text.

    Args:
        text (str): The legal text to parse

    Returns:
        Act: Act object containing 'whom', 'year', and 'number'

    Raises:
        ValueError: If no act information is found in the text
    """
    # First check for specific patterns like "Magistrates' Courts Act"
    # This handles both straight and curly apostrophes
    magistrates_pattern = r"Magistrates[''] Courts Act \((\d+)/(\d{4})\)"
    match_magistrates = re.search(magistrates_pattern, text, re.IGNORECASE)

    if match_magistrates:
        # ic()
        number = int(match_magistrates.group(1))
        year = int(match_magistrates.group(2))
        return Act(whom="Magistrates' Courts", year=year, number=number)

    # Pattern to match acts in the format: "NAME Act (NUMBER/YEAR)"
    # Updated to handle various apostrophes and Unicode characters
    # Using \u2019 for right single quotation mark
    pattern = r"([A-Za-z\s\-'''\u2019]+?)\s+Act\s+\((\d+)/(\d{4})\)"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        # ic()
        whom = match.group(1).strip()
        number = int(match.group(2))
        year = int(match.group(3))

        # Special check: if we only captured "Courts" but "Magistrates" appears before it
        if whom.lower() == "courts":
            # Look for "Magistrates" before this match
            match_start = match.start()
            text_before = text[:match_start]
            if text_before.lower().endswith(
                "magistrates' "
            ) or text_before.lower().endswith("magistrates' "):
                whom = "Magistrates' Courts"

        return Act(whom=whom, year=year, number=number)
    else:
        # ic()
        # Pattern for format: "NAME-Act; YEAR (Act No: NUMBER of YEAR)"
        pattern_semicolon = r"([A-Za-z\s\-'''\u2019]+?)-Act;\s+(\d{4})\s+\(Act\s+No:?\s+(\d+)\s+of\s+\d{4}\)"
        match_semicolon = re.search(pattern_semicolon, text, re.IGNORECASE)

        if match_semicolon:
            # ic()
            whom = match_semicolon.group(1).strip()
            year = int(match_semicolon.group(2))
            number = int(match_semicolon.group(3))

            return Act(whom=whom, year=year, number=number)
        else:
            # ic()
            # Pattern for format: "[NUMBER] NAME Act, No. NUMBER of YEAR"
            pattern_no_format = r"(?:\d+\s+)?([A-Za-z\s\-'''\u2019]+?)\s+Act,\s+No\.\s+(\d+)\s+of\s+(\d{4})"
            match_no_format = re.search(pattern_no_format, text, re.IGNORECASE)

            if match_no_format:
                # ic()
                whom = match_no_format.group(1).strip()
                number = int(match_no_format.group(2))
                year = int(match_no_format.group(3))

                return Act(whom=whom, year=year, number=number)
            else:
                # ic()
                # Pattern for format: "NAME Act, YEAR (Act No. NUMBER of YEAR)"
                pattern_year_paren = r"(?:\d+\s+)?([A-Za-z\s\-'''\u2019]+?)\s+Act,\s+(\d{4})\s+\(Act\s+No\.\s+(\d+)\s+of\s+\d{4}\)"
                match_year_paren = re.search(pattern_year_paren, text, re.IGNORECASE)

                if match_year_paren:
                    # ic()
                    whom = match_year_paren.group(1).strip()
                    year = int(match_year_paren.group(2))
                    number = int(match_year_paren.group(3))

                    return Act(whom=whom, year=year, number=number)
                else:
                    # ic()
                    # Fallback pattern for the older format: "NAME ACT, YEAR (ACT NO: NUMBER OF YEAR)"
                    pattern_old = r"([A-Z''\u2019][A-Z\s'''\u2019]+?)\s+ACT,?\s+(\d{4})\s+\(ACT\s+NO:?\s+(\d+)\s+OF\s+\d{4}\)"
                    match_old = re.search(pattern_old, text, re.IGNORECASE)

                    if match_old:
                        # ic()
                        whom = match_old.group(1).strip()
                        year = int(match_old.group(2))
                        number = int(match_old.group(3))

                        return Act(whom=whom, year=year, number=number)
                    else:
                        # ic()
                        # Special cases here. We need the plumbum line to be joined by
                        # spaces for this one, rather than newlines
                        s = text.replace("\n", " ")
                        if (
                            "with limited authority for the purpose of Exchange Control Regulations"
                            in s
                        ):
                            # ic()
                            return Act(
                                whom="Currency and Exchanges",
                                number=9,
                                year=1933,
                            )
                        else:
                            if len(pages) >= 2:
                                # We can hit an edge-case here where the second
                                # page contains the Act info we want.
                                page2 = pages[1]
                                if (
                                    "Mineral Resources and Energy".lower()
                                    in page2.lower()
                                ):
                                    return Act(
                                        whom="Department of Mineral Resources and Energy",
                                        number=None,
                                        year=None,
                                    )
                                else:
                                    # Special case, we might end up with a bunch of R-prefixed lines here. We can parse through them and look for any specific law detail that match our Notice Number.
                                    if looks_like_pdf_with_r_leading_notices(page2):
                                        act = get_act_leading_r_from_multi_notice_pdf(
                                            text=page2,
                                            notice_number=notice_number,
                                        )
                                        return act
                                    else:
                                        print2("----------------------")
                                        print2(pages[1])
                                        print2("----------------------")
                                        raise UnableToGetActInfo(
                                            "No act information found in the provided text"
                                        )

                            else:
                                print2("----------------------")
                                print2(s)
                                print2("----------------------")
                                raise UnableToGetActInfo(
                                    "No act information found in the provided text"
                                )


##########


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
    n = pdf_gen_n_num
    # Bronnwyn said this recently:
    # "Number range: Currently I believe Procs in the 200s, BNs in the 700s, GenNs in the 3000s and GNs in the 7000s"
    if 200 <= n < 300:
        return MajorType.PROCLAMATION
    elif 700 <= n < 900:
        return MajorType.BOARD_NOTICE
    if 3000 <= n < 4000:
        return MajorType.GENERAL_NOTICE
    elif 6000 <= n < 7000:
        return MajorType.GOVERNMENT_NOTICE
    else:
        raise ValueError(f"Unknown major type for notice number: {pdf_gen_n_num}")
    # Note: List of all of the abbreviations can be found in the footer of the docs
    #       that Bronnwyn gave me


@typechecked
def detect_pdf_year_num(text: str) -> int:
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
    # Pattern: NoAa[.,:] [5-digit-number] [page-number]
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
def looks_like_pdf_with_long_list_of_notices(text: str) -> bool:
    """
    Check if the text contains 3 or more lines that start with 4-digit numbers.

    Args:
        text (str): The input text to check

    Returns:
        bool: True if there are 3+ lines starting with 4-digit numbers, False otherwise
    """
    # Split the text into lines
    lines = text.split("\n")

    match_count = 0

    # Pattern to match a line starting with exactly 4 digits followed by whitespace or non-digit
    pattern = re.compile(r"^(\d{4})(?:\s|[^\d])")

    for line in lines:
        # Strip leading/trailing whitespace for checking
        trimmed_line = line.strip()

        # Check if line starts with 4-digit number
        if trimmed_line and pattern.match(trimmed_line):
            match_count += 1

    return match_count >= 3


@typechecked
def looks_like_pdf_with_r_leading_notices(text: str) -> bool:
    """
    Scan text to check if it contains more than one line starting with
    'R. ' followed by a 3-digit number and a space.

    Args:
        text: The text content to scan

    Returns:
        True if more than one matching line is found, False otherwise
    """
    # Pattern: start of line, "R. ", exactly 3 digits, then a space
    pattern = r"^R\. \d{3} "

    # Split text into lines and count matches
    lines = text.split("\n")
    match_count = 0

    for line in lines:
        if re.match(pattern, line.strip()):
            match_count += 1
            # Early return if we found more than one
            if match_count > 1:
                return True

    return False


@typechecked()
def detect_minor_pdf_type(text: str, pages: list[str], notice_number: int) -> str:
    # Determine the minor type by searching the full text
    full_text_lower = text.lower()
    if "department of sports, arts and culture" in full_text_lower:
        return "Department of Sports, Arts and Culture"
    elif "national astro-tourism" in full_text_lower:
        return "Department of Tourism"
    elif "department of transport" in full_text_lower:
        return "Department of Transport"
    elif "authority for the purpose of exchange control" in full_text_lower:
        return "CURRENCY AND EXCHANGES ACT 9 OF 1933"
    elif "state information technology act" in full_text_lower:
        return "STATE INFORMATION TECHNOLOGY AGENCY ACT 88 OF 1998"
    elif "state information technology act" in full_text_lower:
        return "STATE INFORMATION TECHNOLOGY AGENCY ACT 88 OF 1998"
    elif "mineral resources development bill" in full_text_lower:
        return "BILL"
    else:
        # Over here, we work with types of eg:
        # - ROAD ACCIDENT FUND ACT 56 OF 1996
        # - SKILLS DEVELOPMENT ACT 97 OF 1998
        # - COMPETITION ACT 89 OF 1998
        try:
            act = decode_complex_pdf_type_minor(
                text, pages=pages, notice_number=notice_number
            )
        except UnableToGetActInfo as ex:
            ic()
            logger.exception("Error decoding Act-related details.")
            ic()
            raise ValueError("No act information found in the provided text") from ex
        else:
            return f"{act.whom} ACT {act.number} of {act.year}"


@typechecked
def get_notice_for_gg(
    p: Path, gg_number: int, notice_number: int, cached_llm: CachedLLM
) -> Notice:
    # Grab all text from the PDF file:
    text, pages = load_or_scan_pdf_text(p)

    # Does this look like a PDF that has a long list of notices in it?
    if looks_like_pdf_with_long_list_of_notices(text):
        return get_notice_from_multi_notice_pdf(
            text=text,
            gg_number=gg_number,
            notice_number=notice_number,
            cached_llm=cached_llm,
            pages=pages,
        )

    elif looks_like_pdf_with_r_leading_notices(text):
        # Otherwise, does it look like a list of notices with "R. " in front?
        return get_notice_leading_r_from_multi_notice_pdf(
            text=text,
            gg_number=gg_number,
            notice_number=notice_number,
            cached_llm=cached_llm,
            pages=pages,
        )

    else:
        # Otherwise, it's a regular single-notice PDF
        return get_notice_from_single_notice_pdf(
            text=text,
            gg_number=gg_number,
            notice_number=notice_number,
            cached_llm=cached_llm,
            pages=pages,
        )
