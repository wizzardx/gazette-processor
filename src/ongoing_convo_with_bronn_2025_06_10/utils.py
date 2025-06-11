import json
import os
import re
import sys
from enum import Enum
from pathlib import Path

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
    issn_num: str
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
def get_record_for_gg_num(gg_number: int) -> Notice:
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
def decode_complex_pdf_type_minor(full_text: str) -> Act:
    # Over here, we work with types of eg:
    # - ROAD ACCIDENT FUND ACT 56 OF 1996
    # - SKILLS DEVELOPMENT ACT 97 OF 1998
    # - COMPETITION ACT 89 OF 1998

    # https://claude.ai/chat/e5658a66-f818-46a3-a6fb-af63a4c7968c

    # Pattern to match acts in the format: "NAME ACT, YEAR (ACT NO: NUMBER OF YEAR)"
    pattern = (
        r"([A-Z'][A-Z\s']+?)\s+ACT,?\s+(\d{4})\s+\(ACT\s+NO:?\s+(\d+)\s+OF\s+\d{4}\)"
    )

    match = re.search(pattern, full_text, re.IGNORECASE)

    if match:
        whom = match.group(1).strip()
        year = int(match.group(2))
        number = int(match.group(3))

        return Act(
            whom=whom,
            year=year,
            number=number,
        )
    else:
        assert 0

        return {"whom": None, "year": None, "number": None}


@typechecked
def looks_like_pdf_gen_n_num(n: int) -> bool:
    return 2000 <= n <= 9000


@typechecked
def looks_like_gg_num(n: int) -> bool:
    return 30000 <= n <= 90000


@typechecked
def looks_like_pdf_page_num(n: int) -> bool:
    return 1 <= n <= 100


@typechecked
def get_notice_for_gg(p: Path) -> Notice:
    # Grab all text from the PDF file:
    ic(p)
    pdf_text_list = load_or_scan_pdf_text(p)

    # Combine all pages into a single text string
    full_text = "\n".join([text for page_num, text in pdf_text_list])

    # Convert list to dictionary for easier access by page number (still needed for some operations)
    pdf_text = {}
    for page_num, text in pdf_text_list:
        pdf_text[page_num] = text

    # There is some text that looks like this, which we can use to grab the year (eg 2025) from:
    # "Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025"
    assert pdf_text[1].startswith(
        "Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol:"
    )

    # Split the text up for parsing, eg:
    # ['Government', 'Gazette', 'Staaiskoerant', 'REPUBLIEKVANSUIDAFRIKA', 'Vol:', '719', '23', '2025', 'No:', '52724', 'Mei', 'ISSN', '1682-5845', '2', 'N:B:The', 'Government', 'Printing', 'Works', 'will', 'not:be', 'held', 'responsible', 'for:the', 'quality', 'of', '"Hard', 'Copies"', 'or', '"Electronic', 'Files', 'submitted', 'for', 'publication', 'purposes', 'AIDS', 'HELPLINE:', '0800-0123-22', 'Prevention', 'is', 'the', 'cure', 'May']
    page1_split = pdf_text[1].split()

    # ic(pdf_text)

    @typechecked
    def s(i: int) -> str:
        return page1_split[i]

    @typechecked
    def i(i: int) -> int:
        return int(s(i))

    pdf_vol_num = s(5)
    pdf_monthday_num = i(6)
    pdf_year_num = i(7)
    pdf_gg_num = i(9)
    pdf_monthname_afr_str = s(10)
    pdf_issn_num = s(12)
    pdf_monthname_en_str = s(-1)

    # "Gen" number (eg 3228) and Page No (eg 3) can often be found on page 2 after the word "Contents"
    # PS: Gen is used to differentiate proclamations from other types.
    page2_split = pdf_text[2].split()
    # ic(page2_split)

    # c| page2_split: ['2',
    #                   'No,',
    #                   '52724',
    #                   'IMPORTANT',
    #                   'NOTICE:',
    #                   'BE',
    #                   'HELD',
    #                   'RESPONSIBLE',
    #                   'FOR',
    #                   'ANY',
    #                   'ERRORS',
    #                   'THAT',
    #                   'MIGHT',
    #                   'OCCUR',
    #                   'DUE',
    #                   'To',
    #                   'THE,',
    #                   'SUBMISSION',
    #                   'OF',
    #                   'INCOMPLETE',
    #                   'INCORRECT',
    #                   'ILLEGIBLE',
    #                   'COPY.',
    #                   'Contents',
    #                   'Gazette',
    #                   'Page',
    #                   'No.',
    #                   'No.',
    #                   'No.',
    #                   'GENERAL',
    #                   'NOTICES',
    #                   'ALGEMENE',
    #                   'KENNISGEWINGS',
    #                   'Sports,',
    #                   'Arts',
    #                   'and',
    #                   'Culture,',
    #                   'Department',
    #                   'of',
    #                   '/',
    #                   'Sport;',
    #                   'Kuns',
    #                   'en',
    #                   'Kultuur;',
    #                   'Departement',
    #                   'van',
    #                   '3228',
    #                   'Draft',
    #                   'National',
    #                   'Policy',
    #                   'on',
    #                   'Heritage',
    #                   'Memorialisation:',
    #                   'Publication',
    #                   'of',
    #                   'notice',
    #                   'to',
    #                   'request',
    #                   'public',
    #                   'comment',
    #                   'on-the',
    #                   'draft',
    #                   'National',
    #                   'Policy',
    #                   'Framework',
    #                   'for',
    #                   'Heritage',
    #                   'Memorialisation',
    #                   '_',
    #                   '52724',
    #                   '3']

    contents_seen = False
    pdf_gen_n_num = None
    gg_num_seen = False
    pdf_page_num = None

    for word in page2_split:
        # ic(word)
        if word.isdigit():
            int_word = int(word)
            if contents_seen:
                if pdf_gen_n_num is None and looks_like_pdf_gen_n_num(int_word):
                    pdf_gen_n_num = int_word

                if gg_num_seen is False and looks_like_gg_num(int_word):
                    gg_num_seen = True

                if pdf_page_num is None and looks_like_pdf_page_num(int_word):
                    pdf_page_num = int_word

                # # The next number is the "Gen N" number, eg 3228
                # if pdf_gen_n_num is None:
                #     # Ignore values of 0 here, rather than populating pdf_gen_n_num
                #     if int_word == 0:
                #         continue
                #     else:
                #         pdf_gen_n_num = int(word)
                # elif not gg_num_seen:
                #     # The next number after that is the gg number, eg 52724, or it
                #     # might be a year number
                #     if looks_like_a_year_string(word):
                #         continue
                #     assert int(word) == int(pdf_gg_num)
                #     gg_num_seen = True
                # elif pdf_page_num is None:
                #     # This is the page number where the law info can be found eg 3
                #     pdf_page_num = int(word)
                # else:
                #     # Skip any additional numbers after we have what we need
                #     pass
        elif word == "Contents":
            contents_seen = True
        else:
            continue

    # Determine the major type by searching the full text
    full_text_lower = full_text.lower()
    if "general notice" in full_text_lower:
        pdf_type_major = MajorType.GENERAL_NOTICE
    elif "government notice" in full_text_lower:
        pdf_type_major = MajorType.GOVERNMENT_NOTICE
    elif "magistrates' courts act" in full_text_lower:
        pdf_type_major = MajorType.GOVERNMENT_NOTICE
    else:
        ic(full_text_lower[:500])
        raise ValueError(f"Unknown major type in full text: {full_text_lower[:100]}...")

    # Determine the minor type by searching the full text
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

    # Now we want something that looks like this:

    "Draft National Policy Framework for Heritage Memorialisation published for comment"

    # Where what we have in page 2 is this:

    # ic| pdf_text[2]: ('2 No, 52724 IMPORTANT NOTICE: BE HELD RESPONSIBLE FOR ANY   ERRORS THAT '
    #                   'MIGHT OCCUR DUE To THE, SUBMISSION OF INCOMPLETE INCORRECT ILLEGIBLE COPY. '
    #                   'Contents Gazette Page No. No. No. GENERAL NOTICES ALGEMENE KENNISGEWINGS '
    #                   'Sports, Arts and Culture, Department of / Sport; Kuns en Kultuur; '
    #                   'Departement van 3228 Draft National Policy on Heritage Memorialisation: '
    #                   'Publication of notice to request public comment on-the draft National Policy '
    #                   'Framework for Heritage Memorialisation _ 52724 3')
    # Traceback (most recent call last):

    # It seems we should be able to get the text between the pdf_issn_num and the underscore
    gen_n_num_seen = False
    words_to_use = []
    for word in pdf_text[2].split():
        # print(repr(word))
        if word == str(pdf_gen_n_num):
            gen_n_num_seen = True
        elif gen_n_num_seen:
            if word == "_":
                break
            else:
                words_to_use.append(word)
        else:
            continue

    pdf_text_content = " ".join(words_to_use)
    # Also in PDF Page 3: if we don't have the Notice's Page Number yet, then
    # then we can sometimes find it there. eg:

    # 3: 'STAATSKOERANT; 23 MEI-2025 No; 52726 3 GovERNMENT NoTICES '
    #    'GoEWERMENTSKENNISGEWINGS DEPARTMENT OF TRANSPORT NO. 6220 23 2025 DRAFT '
    #    'COMPREHENSIVE CIVIL AVIATION POLICY The comments: Interested persons '
    #    'are   requested to   submit written   comments in connection with-the '
    #    'Draft Comprehensive Civil Aviation Policy within 30.days from the date of '
    #    'publication of this notice in the Government Gazette. All comments should '
    #    'be posted or emailed to the Director- General of the Department-of '
    #    'Transport for the attention-of Ms. Johannah Sekele as follows: Department '
    #    'of Transport Private Bag X 193 Pretoria 0001 Email: SekeleJ@dot_govza and '
    #    'TholoT@dotgovza Tel: 012 309 3760 May',

    if pdf_page_num is None:
        # Try to find page number from page 3 text specifically
        page3_text_lower = pdf_text[3].lower() if 3 in pdf_text else ""
        pdf_page_num = attempt_to_get_pdf_page_num(
            pdf_gg_num=pdf_gg_num, page_text_lower=page3_text_lower
        )

    # Ensure all required fields are not None
    if pdf_gen_n_num is None:
        # ic(pdf_text)
        raise ValueError("Could not find gen_n_num in PDF")
    if pdf_page_num is None:
        # ic(pdf_text)
        raise ValueError("Could not find page number in PDF")

    return Notice(
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
