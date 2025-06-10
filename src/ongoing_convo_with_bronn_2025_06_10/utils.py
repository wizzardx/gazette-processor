from typeguard import typechecked
from enum import Enum
import os
import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from validation_helpers import StrictBaseModel
from enhanced_ocr import extract_pdf_text
from icecream import ic


class Record(StrictBaseModel):
    gen_n_num: int
    gg_num: int
    monthday_num: int
    month_name: str
    year: int
    page: int
    issn_num: str
    type_major: 'MajorType'
    type_minor: str
    text: str


class MajorType(Enum):
    GENERAL_NOTICE = 'GENERAL_NOTICE'


@typechecked
def load_or_scan_pdf_text(p: Path) -> list[tuple[int, str]]:
    # Create cache directory if it doesn't exist
    if not os.path.exists("cache"):
        os.makedirs("cache")
    
    # Generate cache filename based on PDF filename
    pdf_basename = p.name
    cache_filename = pdf_basename.replace('.pdf', '_ocr_cache.json')
    cache_fname_path = Path("cache") / cache_filename
    
    # Check if cache file exists
    if cache_fname_path.exists():
        # Load from cache
        with open(cache_fname_path, 'r') as f:
            cached_data = json.load(f)
        # Convert to expected format: list of (page_num, text) tuples
        return [(page_num, text) for page_num, text, _ in cached_data]
    else:
        # Perform OCR
        ocr_results = extract_pdf_text(p)
        
        # Save to cache
        with open(cache_fname_path, 'w') as f:
            json.dump(ocr_results, f, indent=2)
        
        # Return in expected format: list of (page_num, text) tuples
        return [(page_num, text) for page_num, text, _ in ocr_results]


GG_DIR = Path('/home/david/dev/misc/bronnwyn-stuff/bulletin-generator-rnd/files_from_bronnwyn/2025-05-28/David Bulletin/Source GGs/2025/')


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
def get_record_for_gg_num(gg_number: int) -> Record:
    p = locate_gg_pdf_by_number(gg_number)
    return get_record_for_gg(p)


@typechecked
def looks_like_a_year_string(s: str) -> bool:
    if not s.isdigit():
        return False
    if len(s) != 4:
        return False
    year = int(s)
    return 1900 <= year <= 2100


@typechecked
def get_record_for_gg(p: Path) -> Record:
    # Grab all text from the PDF file:
    ic(p)
    pdf_text_list = load_or_scan_pdf_text(p)
    
    # Convert list to dictionary for easier access by page number
    pdf_text = {}
    for page_num, text in pdf_text_list:
        pdf_text[page_num] = text

    # There is some text that looks like this, which we can use to grab the year (eg 2025) from:
    # "Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025"
    assert pdf_text[1].startswith("Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol:")

    # Split the text up for parsing, eg:
    # ['Government', 'Gazette', 'Staaiskoerant', 'REPUBLIEKVANSUIDAFRIKA', 'Vol:', '719', '23', '2025', 'No:', '52724', 'Mei', 'ISSN', '1682-5845', '2', 'N:B:The', 'Government', 'Printing', 'Works', 'will', 'not:be', 'held', 'responsible', 'for:the', 'quality', 'of', '"Hard', 'Copies"', 'or', '"Electronic', 'Files', 'submitted', 'for', 'publication', 'purposes', 'AIDS', 'HELPLINE:', '0800-0123-22', 'Prevention', 'is', 'the', 'cure', 'May']
    page1_split = pdf_text[1].split()

    # ic(pdf_text)

    def s(i: int) -> str:
        return page1_split[i]

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
        # print(word)
        if word.isdigit():
            if contents_seen:
                # The next number is the "Gen N" number, eg 3228
                if pdf_gen_n_num is None:
                    pdf_gen_n_num = int(word)
                elif not gg_num_seen:
                    # The next number after that is the gg number, eg 52724, or it
                    # might be a year number
                    if looks_like_a_year_string(word):
                        continue
                    assert int(word) == int(pdf_gg_num)
                    gg_num_seen = True
                elif pdf_page_num is None:
                    # This is the page number where the law info can be found eg 3
                    pdf_page_num = int(word)
                else:
                    # Skip any additional numbers after we have what we need
                    pass
        elif word == "Contents":
            contents_seen = True
        else:
            continue

    # In page 3 we can determine a few useful things, starting with what I call the "major type", eg "PROCLAMATIONS" or "NOTICES"
    page3_text_lower = pdf_text[3].lower()
    match = "general notice"
    if match in page3_text_lower:
        pdf_type_major = MajorType.GENERAL_NOTICE
    else:
        ic(page3_text_lower)
        raise ValueError(f"Unknown major type in page 3 text: {page3_text_lower[:100]}...")

    # Also something similar to "Department of Sports, Arts and Culture"
    if "department of sports, arts and culture" in page3_text_lower:
        pdf_type_minor = "Department of Sports, Arts and Culture"
    elif "national astro-tourism" in page3_text_lower:
        pdf_type_minor = "Department of Tourism"
    else:
        ic(page3_text_lower)
        assert 0

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
            if word == '_':
                break
            else:
                words_to_use.append(word)
        else:
            continue

    pdf_text_content = ' '.join(words_to_use)

    # Ensure all required fields are not None
    if pdf_gen_n_num is None:
        raise ValueError("Could not find gen_n_num in PDF")
    if pdf_page_num is None:
        raise ValueError("Could not find page number in PDF")
    
    return Record(
        gen_n_num = pdf_gen_n_num,
        gg_num = pdf_gg_num,
        monthday_num = pdf_monthday_num,
        month_name = pdf_monthname_en_str,
        year = pdf_year_num,
        page = pdf_page_num,
        issn_num = pdf_issn_num,
        type_major = pdf_type_major,
        type_minor = pdf_type_minor,
        text = pdf_text_content,
    )
