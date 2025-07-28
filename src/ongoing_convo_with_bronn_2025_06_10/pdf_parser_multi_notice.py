import logging
import re
from typing import Any, Optional

from typeguard import typechecked

from .cached_llm import CachedLLM
from .common_types import Act, MajorType, Notice

logger = logging.getLogger(__name__)


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


# Claude is helping with this function:
# https://claude.ai/chat/e029ab6a-209f-47bb-8ed4-3626a4101043

############


def _extract_logical_lines(text: str) -> list[str]:
    """
    RECOMMENDED FUNCTION: Use this function to extract logical lines from your text.

    This function robustly handles edge cases including:
    - Lines without dots (like 3379) being incorrectly merged with subsequent lines
    - Continuation lines (like "2025 ........... 53025 81") being treated as separate entries
    - Text that doesn't rely on consistent newline formatting

    Args:
        text (str): The input text containing logical lines

    Returns:
        list[str]: List of cleaned logical lines, each starting with a 3-4 digit number

    Example:
        logical_lines = _extract_logical_lines(your_text)
    """
    logical_lines = []

    # Split into lines first to make processing easier
    lines = text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if this line starts a logical entry
        start_match = re.match(r"^(\d{3,4})\s+", line)
        if not start_match:
            i += 1
            continue

        # Start building the logical line
        logical_line_parts = [line]

        # Look ahead for continuation lines or end pattern
        j = i + 1
        found_end = False

        # Check if current line already has the end pattern
        if re.search(r"\.{3,}\s+\d+\s+\d+\s*$", line):
            found_end = True
        elif re.search(r"\s+\d+\s+\d+\s*$", line):
            # Line ends with just numbers (like line 3379)
            found_end = True

        # If we haven't found the end, look at subsequent lines
        while j < len(lines) and not found_end:
            next_line = lines[j].strip()

            # Check if next line starts a new logical entry (and isn't a continuation)
            next_start_match = re.match(r"^(\d{3,4})\s+", next_line)

            if next_start_match:
                # Check if this is a continuation line (starts with year + lots of dots)
                content_after_number = next_line[len(next_start_match.group(0)) :]
                is_year_continuation = (
                    len(next_start_match.group(1)) == 4  # 4-digit number (year)
                    and re.search(r"\.{10,}", content_after_number)  # Lots of dots
                    and re.search(
                        r"\.{3,}\s+\d+\s+\d+\s*$", next_line
                    )  # Ends with pattern
                    and not re.search(
                        r"[A-Za-z]{10,}", content_after_number
                    )  # Not much text content
                )

                if is_year_continuation:
                    # This is a continuation line
                    logical_line_parts.append(next_line)
                    found_end = True
                    j += 1
                    break
                else:
                    # This is a new logical line start, stop here
                    break
            else:
                # Not a start line, could be a continuation
                logical_line_parts.append(next_line)

                # Check if this line has the end pattern
                if re.search(r"\.{3,}\s+\d+\s+\d+\s*$", next_line):
                    found_end = True
                    j += 1
                    break

            j += 1

        # Join the parts and clean up
        full_logical_line = " ".join(logical_line_parts)
        cleaned_line = re.sub(r"\s+", " ", full_logical_line).strip()

        if cleaned_line:
            logical_lines.append(cleaned_line)

        # Move to the next unprocessed line
        i = j

    return logical_lines


def get_act_from_multi_notice_pdf(text: str, notice_number: int) -> Act:
    logical_lines = _extract_logical_lines(text)

    for line in logical_lines:
        if str(notice_number) in line:
            parsed = _parse_single_entry(line)
            if parsed is not None:
                return Act(
                    whom=parsed["law_description"],
                    year=parsed["law_year"],
                    number=parsed["law_number"],
                )
    assert 0


############

# Claude is helping with this function over here:
# https://claude.ai/chat/efbd9b10-8f19-4e4a-a7c4-c99c0731d8d5

#########


def _parse_single_entry(logical_line: str) -> Optional[dict[str, Any]]:
    """
    Internal function to parse a single logical line into structured data.
    """

    # Pattern to extract all components
    # Groups: (1) notice_number (2) content before dots (3) gazette_number (4) page_number
    main_pattern = re.compile(r"^(\d{3,4})\s+(.+?)\.{3,}\s+(\d+)\s+(\d+)\s*$")

    match = main_pattern.match(logical_line)
    if not match:
        logger.debug("Failed to match line pattern:")
        logger.debug(logical_line)
        logger.debug("------------")
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
    # 6. Simple format: "Something Act, 56 of 1996" (without "No.")
    # 7. Afrikaans ending in "wet": "Somethingwet, No. 56 van 1996"

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
            # Try simple format without "No.": "Something Act, 56 of 1996"
            act_pattern_simple = re.compile(
                r"^(.+?)\s+Act,\s*(\d+)\s+of\s+(\d{4})", re.IGNORECASE
            )
            act_match = act_pattern_simple.search(content)

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
                                r"^(.+?wet),\s*No\.?\s*(\d+)\s+van\s+(\d{4})",
                                re.IGNORECASE,
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
        logger.debug("Unable to extract Act details from line:")
        logger.debug(logical_line)
        logger.debug("-----------")
        return None
        # raise ValueError("Unable to extract Act details from a string")

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


#########


@typechecked
def get_notice_from_multi_notice_pdf(
    text: str,
    gg_number: int,
    notice_number: int,
    cached_llm: CachedLLM,
    pages: list[str],
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
                # print(f"Notice #{notice_number} was seen multiple times")
                pass
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
    pdf_type_minor = detect_minor_pdf_type(
        match["logical_line"], pages=pages, notice_number=notice_number
    )
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
