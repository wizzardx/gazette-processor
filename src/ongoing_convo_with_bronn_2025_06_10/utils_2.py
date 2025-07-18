import re
from pathlib import Path
from typing import Iterator

from icecream import ic
from tqdm import tqdm
from typeguard import typechecked

from .cached_llm import CachedLLM
from .common_types import Notice
from .prints import print1, print2
from .utils import get_notice_for_gg_num, load_or_scan_pdf_text

#
# GG_DIR = Path(
#     "/home/david/dev/misc/bronnwyn-stuff/bulletin-generator-rnd/files_from_bronnwyn/2025-05-28/David Bulletin/Source GGs/2025/"
# )


def output_testing_bulletin_2(gg_dir: Path) -> None:
    cached_llm = CachedLLM()

    # Get all the filename paths in advance so that we can show progress progressing through all of them.
    paths = []
    for p in gg_dir.iterdir():
        # if p.is_file() and p.name.startswith("gg") and p.name.endswith(".pdf"):
        if p.is_file() and p.name.endswith(".pdf"):
            print2(f"Found GG PDF: {p.name}")
            paths.append(p)

    # Now we can use tqdm:
    for p in tqdm(sorted(paths)):
        # Here you would call your function to process the PDF
        # For example:
        for notice in find_notices_in_pdf(p=p, cached_llm=cached_llm, gg_dir=gg_dir):
            print2(notice.text)


@typechecked
def extract_gg_num_from_pdf_filename(filename: str) -> int:
    # Extract 5-digit number starting with 5, after 'gg' and before '_'
    match = re.search(r"(5\d{4})", filename)
    assert match, repr((match, filename))
    return int(match.group(1))


@typechecked
def search_for_prospective_gg_nums(text: str) -> Iterator[int]:
    # Search for prospective 3 or 4-digit characters within the text, and convert
    # and yield them one at a time:
    # First get
    # Pattern to match 3 or 4 digit numbers (not part of longer numbers)
    pattern = r"\b\d{3,4}\b"

    # Find all matches and convert to a set of integers (removes duplicates)
    matches = re.findall(pattern, text)
    unique_numbers = set(int(match) for match in matches)

    # Yield each unique number in ascending order
    for num in sorted(unique_numbers):
        yield num


@typechecked
def find_notices_in_pdf(
    p: Path, cached_llm: CachedLLM, gg_dir: Path
) -> Iterator[Notice]:
    # We have the notice filename (containining the notice number), and the
    # cached LLM. Next, we can try to brute force all of our methods across
    # the PDF file

    # First extract the Gazette Number:
    gazette_number = extract_gg_num_from_pdf_filename(p.name)

    # Load the text, then locate all the 3 or 4-digit numbers (our
    # prospective Notice Numbers, and then try to match them and our GG numbers
    # together as "lookup" pairs across all of the lookup methoids.

    # Use plumbum to convert to text:
    text, pages = load_or_scan_pdf_text(p)

    # Now find all the 3 and 4-digit integers within the text:
    for notice_number in search_for_prospective_gg_nums(text):
        try:
            notice = get_notice_for_gg_num(
                gg_number=gazette_number,
                notice_number=notice_number,
                cached_llm=cached_llm,
                gg_dir=gg_dir,
            )
        except Exception as ex:
            # We expect most of these to be errors
            print2(f"Ignoring error {ex}")
        else:
            # We actually found something?
            with open("output/output.csv", "a") as f:
                f.write(f"{notice_number},{gazette_number}\n")
            yield notice
