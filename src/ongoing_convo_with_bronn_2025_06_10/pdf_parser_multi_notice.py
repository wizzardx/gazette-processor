import re
from typing import Any, Optional

from typeguard import typechecked

from .cached_llm import CachedLLM
from .common_types import MajorType, Notice


@typechecked
def parse_gazette_document(text: str) -> list[dict[str, Any]]:
    """
    Parse a complete gazette document and return structured data.

    Args:
        text: The full gazette document text

    Returns:
        List of dictionaries, where each dictionary contains:
        - logical_line (str): The complete joined line
        - notice_number (int): The 4-digit notice number
        - law_description (str): What the law is about (e.g., "Subdivision of Agricultural Land")
        - law_number (int or None): Number of the law within the year (e.g., 70)
        - law_year (int or None): Year the law was for (e.g., 1970)
        - gazette_number (int): Gazette number (e.g., 52712)
        - page_number (int): Page number (e.g., 14)
        - notice_description (str): The human-readable description of the notice
          (e.g., "Intention for the exclusion of certain properties from the provisions
           of the subdivision of the Act in various municipalities within the
           Republic of South Africa (30 days notice for comments)")
    """
    # First, join split logical lines
    logical_lines = _extract_logical_lines(text)

    # Parse each logical line into structured data
    parsed_entries = []
    for line in logical_lines:
        entry = _parse_single_entry(line)
        if entry:
            parsed_entries.append(entry)

    return parsed_entries


def _extract_logical_lines(text: str) -> list[str]:
    """
    Internal function to join split logical lines into single lines.
    """
    lines = text.split("\n")
    logical_lines = []
    current_logical_line: list[str] = []
    in_logical_line = False

    # Pattern to match the start of a logical line (3 of 4-digit code at line start)
    start_pattern = re.compile(r"^\d{3,4}\s+")

    # Pattern to match the end of a logical line (dots followed by numbers)
    end_pattern = re.compile(r"\.{3,}\s+\d+\s+\d+\s*$")

    for line in lines:
        # Check if this line starts a new logical line
        if start_pattern.match(line):
            # If we were already building a logical line, save it first
            if current_logical_line:
                logical_lines.append(" ".join(current_logical_line))

            # Start new logical line
            current_logical_line = [line.strip()]
            in_logical_line = True

            # Check if this line also ends the logical line (single-line entry)
            if end_pattern.search(line):
                logical_lines.append(" ".join(current_logical_line))
                current_logical_line = []
                in_logical_line = False

        elif in_logical_line:
            # Continue building the current logical line
            current_logical_line.append(line.strip())

            # Check if this line ends the logical line
            if end_pattern.search(line):
                logical_lines.append(" ".join(current_logical_line))
                current_logical_line = []
                in_logical_line = False

    # Don't forget any remaining logical line
    if current_logical_line:
        logical_lines.append(" ".join(current_logical_line))

    return logical_lines


def _parse_single_entry(logical_line: str) -> Optional[dict[str, Any]]:
    """
    Internal function to parse a single logical line into structured data.
    """
    # Pattern to extract all components
    # Groups: (1) notice_number (2) content before dots (3) gazette_number (4) page_number
    main_pattern = re.compile(r"^(\d{3,4})\s+(.+?)\.{3,}\s+(\d+)\s+(\d+)\s*$")

    match = main_pattern.match(logical_line)
    if not match:
        print("------------")
        print(logical_line)
        print("------------")
        assert 0
        return None

    notice_number = int(match.group(1))
    content = match.group(2).strip()
    gazette_number = int(match.group(3))
    page_number = int(match.group(4))

    # Extract law information from content
    # Try multiple patterns:
    # 1. Standard format: "Something Act (3/1996)"
    # 2. Alternative format: "Something Act (Act No.36 of 1947)" or "(No.36 of 1947)"
    # 3. Year after Act: "Something Act, 2002 (Act No. 71 of 2002)"
    # 4. Afrikaans format: "Wet op Something (28/2011)"
    # 5. No parentheses format: "Something Act, No. 56 of 1996"
    # 6. Afrikaans ending in "wet": "Somethingwet, No. 56 van 1996"

    act_match = None
    law_description = None
    law_number = None
    law_year = None

    # First try standard English format
    act_pattern_standard = re.compile(
        r"^(.+?)\s+Act\s*\((\d+)/(\d{4})\)", re.IGNORECASE
    )
    act_match = act_pattern_standard.search(content)

    if act_match:
        law_description = act_match.group(1).strip()
        law_number = int(act_match.group(2))
        law_year = int(act_match.group(3))
    else:
        # Try format without parentheses: "Something Act, No. 56 of 1996"
        act_pattern_no_parens = re.compile(
            r"^(.+?)\s+Act,\s*No\.?\s*(\d+)\s+of\s+(\d{4})", re.IGNORECASE
        )
        act_match = act_pattern_no_parens.search(content)

        if act_match:
            law_description = act_match.group(1).strip()
            law_number = int(act_match.group(2))
            law_year = int(act_match.group(3))
        else:
            # Try format with year after Act: "Something Act, 2002 (Act No. 71 of 2002)"
            act_pattern_with_year = re.compile(
                r"^(.+?)\s+Act,\s*(\d{4})\s*\((?:Act\s+)?No\.?\s*(\d+)\s+of\s+\d{4}\)",
                re.IGNORECASE,
            )
            act_match = act_pattern_with_year.search(content)

            if act_match:
                law_description = act_match.group(1).strip()
                law_year = int(act_match.group(2))
                law_number = int(act_match.group(3))
            else:
                # Try alternative English format with "Act No." or "No."
                act_pattern_alternative = re.compile(
                    r"^(.+?)\s+Act\s*\((?:Act\s+)?No\.?\s*(\d+)\s+of\s+(\d{4})\)",
                    re.IGNORECASE,
                )
                act_match = act_pattern_alternative.search(content)

                if act_match:
                    law_description = act_match.group(1).strip()
                    law_number = int(act_match.group(2))
                    law_year = int(act_match.group(3))
                else:
                    # Try Afrikaans format - Wet at the beginning
                    act_pattern_afrikaans = re.compile(
                        r"^Wet\s+(.+?)\s*\((\d+)/(\d{4})\)", re.IGNORECASE
                    )
                    act_match = act_pattern_afrikaans.search(content)

                    if act_match:
                        # For Afrikaans format, prepend "Wet" to the description
                        law_description = "Wet " + act_match.group(1).strip()
                        law_number = int(act_match.group(2))
                        law_year = int(act_match.group(3))
                    else:
                        # Try Afrikaans format ending in "wet" without parentheses: "Somethingwet, No. 56 van 1996"
                        act_pattern_afrikaans_no_parens = re.compile(
                            r"^(.+?wet),\s*No\.?\s*(\d+)\s+van\s+(\d{4})", re.IGNORECASE
                        )
                        act_match = act_pattern_afrikaans_no_parens.search(content)

                        if act_match:
                            law_description = act_match.group(1).strip()
                            law_number = int(act_match.group(2))
                            law_year = int(act_match.group(3))
                        else:
                            # Try Afrikaans format ending in "wet" with parentheses: "Somethingwet (No. 56 van 1996)"
                            act_pattern_afrikaans_with_parens = re.compile(
                                r"^(.+?wet)\s*\((?:No\.?\s*)?(\d+)\s+van\s+(\d{4})\)",
                                re.IGNORECASE,
                            )
                            act_match = act_pattern_afrikaans_with_parens.search(
                                content
                            )

                            if act_match:
                                law_description = act_match.group(1).strip()
                                law_number = int(act_match.group(2))
                                law_year = int(act_match.group(3))

    if act_match:
        # Extract the notice description (everything after the Act info)
        # Find where the Act match ends
        act_end = act_match.end()
        remaining_content = content[act_end:].strip()

        # Remove any parenthetical abbreviations like ("the LTA")
        remaining_content = re.sub(
            r'\s*\(["\'].*?["\']\)\s*', " ", remaining_content
        ).strip()

        # Remove leading colons and whitespace
        notice_description = remaining_content.lstrip(":").strip()
    else:
        print("-----------")
        print(logical_line)
        print("-----------")
        raise ValueError("Unable to extract Act details from a string")

    return {
        "logical_line": logical_line,
        "notice_number": notice_number,
        "law_description": law_description,
        "law_number": law_number,
        "law_year": law_year,
        "gazette_number": gazette_number,
        "page_number": page_number,
        "notice_description": notice_description,
    }


@typechecked
def get_notice_from_multi_notice_pdf(
    text: str, gg_number: int, notice_number: int, cached_llm: CachedLLM
) -> Notice:
    """
    Extract a specific notice from a PDF containing multiple notices.

    Args:
        text: The full PDF text
        gg_number: Government Gazette number
        notice_number: The specific notice number to extract
        cached_llm: LLM instance for text summarization

    Returns:
        Notice object with the extracted information
    """
    # Parse our text into a convenient structure for handling in this function:
    rows = parse_gazette_document(text)

    # Find the matching notice:
    match = None
    for row in rows:
        if row["notice_number"] == notice_number:
            if match is not None:
                print(f"Notice #{notice_number} was seen multiple times")
            else:
                # We work with the first version in our report (often English)
                match = row
    if match is None:
        raise ValueError(f"Unable to find details for notice {notice_number}")

    # Some sanity checks
    assert match["gazette_number"] == gg_number
    assert match["notice_number"] == notice_number

    # Import detection functions to avoid circular imports
    from .utils import (
        detect_issn_num,
        detect_major_type_from_notice_number,
        detect_minor_pdf_type,
        detect_monthday_en_str,
        detect_monthday_num,
        detect_pdf_year_num,
    )

    pdf_monthday_num = detect_monthday_num(text)
    pdf_monthname_en_str = detect_monthday_en_str(text)
    pdf_year_num = detect_pdf_year_num(text)
    pdf_page_num = match["page_number"]
    pdf_issn_num = detect_issn_num(text)
    pdf_type_major = detect_major_type_from_notice_number(notice_number)
    pdf_type_minor = detect_minor_pdf_type(match["logical_line"])
    pdf_text = cached_llm.summarize(match["notice_description"])

    return Notice(
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
