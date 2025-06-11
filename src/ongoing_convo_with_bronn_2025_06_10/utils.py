import json
import os
import re
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from typeguard import typechecked

# Add the project root to the path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from icecream import ic

from enhanced_ocr import extract_pdf_text
from validation_helpers import StrictBaseModel


class Notice(StrictBaseModel):
    gen_n_num: int
    gg_num: int
    monthday_num: int
    month_name: str
    year: int
    page: int
    issn_num: Optional[str]
    type_major: "MajorType"
    type_minor: str
    text: str


class MajorType(Enum):
    GENERAL_NOTICE = "GENERAL_NOTICE"
    GOVERNMENT_NOTICE = "GOVERNMENT_NOTICE"


@typechecked
def load_or_scan_pdf_text(p: Path) -> list[tuple[int, str]]:
    # Create cache directory if it doesn't exist
    if not os.path.exists("cache"):
        os.makedirs("cache")

    # Generate cache filename based on PDF filename
    pdf_basename = p.name
    cache_filename = pdf_basename.replace(".pdf", "_ocr_cache.json")
    cache_fname_path = Path("cache") / cache_filename

    # Check if cache file exists
    if cache_fname_path.exists():
        # Load from cache
        with open(cache_fname_path, "r") as f:
            cached_data = json.load(f)
        # Convert to expected format: list of (page_num, text) tuples
        return [(page_num, text) for page_num, text, _ in cached_data]
    else:
        # Perform OCR
        ocr_results = extract_pdf_text(p)

        # Save to cache
        with open(cache_fname_path, "w") as f:
            json.dump(ocr_results, f, indent=2)

        # Return in expected format: list of (page_num, text) tuples
        return [(page_num, text) for page_num, text, _ in ocr_results]


GG_DIR = Path(
    "/home/david/dev/misc/bronnwyn-stuff/bulletin-generator-rnd/files_from_bronnwyn/2025-05-28/David Bulletin/Source GGs/2025/"
)


@typechecked
def locate_gg_pdf_by_number(gg_number: int) -> Path:
    gg_s = str(gg_number)
    result = None
    for p in GG_DIR.iterdir():
        if gg_s in p.name:
            assert result is None
            result = p
    assert result is not None
    return result


@typechecked
def get_notice_for_gg_num(gg_number: int) -> Notice:
    p = locate_gg_pdf_by_number(gg_number)
    return get_notice_for_gg(p)


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
def decode_complex_pdf_type_minor(text: str) -> Act:
    # Over here, we work with types of eg:
    # - ROAD ACCIDENT FUND ACT 56 OF 1996
    # - SKILLS DEVELOPMENT ACT 97 OF 1998
    # - COMPETITION ACT 89 OF 1998
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

    # Pattern to match acts in the format: "NAME Act (NUMBER/YEAR)"
    pattern = r"([A-Za-z\s\-']+?)\s+Act\s+\((\d+)/(\d{4})\)"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        whom = match.group(1).strip()
        number = int(match.group(2))
        year = int(match.group(3))

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
    if 3000 < pdf_gen_n_num < 4000:
        return MajorType.GENERAL_NOTICE
    elif 6000 < pdf_gen_n_num < 7000:
        return MajorType.GOVERNMENT_NOTICE
    else:
        raise ValueError(f"Unknown major type for notice number: {pdf_gen_n_num}")


@typechecked
def get_notice_for_gg(p: Path) -> Notice:
    # Grab all text from the PDF file:
    ic(p)
    pdf_text_list = load_or_scan_pdf_text(p)

    # Combine all text into a single string
    full_text = "\n".join([text for page_num, text in pdf_text_list])
    ic(full_text)

    # Find the header text that contains volume and date information
    header_marker = "Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol:"
    header_start = full_text.find(header_marker)
    assert header_start != -1, f"Could not find header marker in PDF text"

    # Extract the header line
    header_end = full_text.find("\n", header_start)
    if header_end == -1:
        header_text = full_text[header_start:]
    else:
        header_text = full_text[header_start:header_end]

    # Split the header text for parsing
    header_split = header_text.split()

    # ic(full_text)

    @typechecked
    def s(i: int) -> str:
        return header_split[i]

    @typechecked
    def i(i: int) -> int:
        return int(s(i))

    pdf_vol_num = s(5)
    pdf_monthday_num = i(6)
    pdf_year_num = i(7)
    pdf_gg_num = i(9)
    pdf_monthname_afr_str = s(10)
    pdf_issn_num: Optional[str] = s(12)

    # Sometimes the word "Government" appears instead of the ISSN number in the
    # scanned text. What this means is that the OCR'd text did not include the
    # ISSN.
    if pdf_issn_num == "Government":
        pdf_issn_num = None

    pdf_monthname_en_str = s(-1)

    # Find the "Contents" section in the full text
    contents_marker = "Contents"
    contents_start = full_text.find(contents_marker)
    assert contents_start != -1, "Could not find Contents section"

    # Extract text after "Contents" to look for Gen number and page info
    contents_text = full_text[contents_start:]
    contents_split = contents_text.split()
    # ic(contents_split)

    # Parse the contents section to find Gen number and page info
    pdf_gen_n_num = None
    gg_num_seen = False
    pdf_page_num = None

    for idx, word in enumerate(contents_split):
        # Skip the first occurrence of "Contents" since we already found it
        if idx == 0 and word == "Contents":
            continue

        # ic(word)
        if word.isdigit():
            int_word = int(word)
            if pdf_gen_n_num is None and looks_like_pdf_gen_n_num(int_word):
                pdf_gen_n_num = int_word

            if gg_num_seen is False and looks_like_gg_num(int_word):
                gg_num_seen = True

            if pdf_page_num is None and looks_like_pdf_page_num(int_word):
                pdf_page_num = int_word

    # Determine the major type by checking the Notice Number
    if pdf_gen_n_num is None:
        raise ValueError("Unable to determine a Notice Number")
    pdf_type_major = detect_major_type_from_notice_number(pdf_gen_n_num)

    # Determine the minor type by searching the full text
    full_text_lower = full_text.lower()
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
        act = decode_complex_pdf_type_minor(full_text)
        pdf_type_minor = f"{act.whom} ACT {act.number} of {act.year}"

    # Extract the notice description text
    # Find the gen_n_num in the contents section and get text after it
    gen_n_num_seen = False
    words_to_use = []

    # Look for the gen number in the contents text and extract description after it
    for word in contents_split:
        if word == str(pdf_gen_n_num):
            gen_n_num_seen = True
        elif gen_n_num_seen:
            if word == "_":
                break
            else:
                words_to_use.append(word)

    pdf_text_content = " ".join(words_to_use)
    # If we don't have the page number yet, try to find it in the full text
    if pdf_page_num is None:
        # Look for pattern like "STAATSKOERANT; 23 MEI-2025 No; 52726 3"
        full_text_lower = full_text.lower()
        pdf_page_num = attempt_to_get_pdf_page_num(
            pdf_gg_num=pdf_gg_num, page_text_lower=full_text_lower
        )

    # Ensure all required fields are not None
    if pdf_gen_n_num is None:
        # ic(full_text[:1000])
        raise ValueError("Could not find gen_n_num in PDF")
    if pdf_page_num is None:
        # ic(full_text[:1000])
        raise ValueError("Could not find page number in PDF")

    notice = Notice(
        gen_n_num=pdf_gen_n_num,
        gg_num=pdf_gg_num,
        monthday_num=pdf_monthday_num,
        month_name=pdf_monthname_en_str,
        year=pdf_year_num,
        page=pdf_page_num,
        issn_num=pdf_issn_num,
        type_major=pdf_type_major,
        type_minor=pdf_type_minor,
        text=pdf_text_content,
    )
    ic(notice)
    return notice
