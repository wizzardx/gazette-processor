from typeguard import typechecked

from .cached_llm import CachedLLM
from .common_types import MajorType, Notice


@typechecked
def get_notice_from_single_notice_pdf(
    text: str,
    gg_number: int,
    notice_number: int,
    cached_llm: CachedLLM,
    pages: list[str],
) -> Notice:
    """
    Extract notice information from a PDF containing a single notice.

    Args:
        text: The full PDF text
        gg_number: Government Gazette number
        notice_number: The notice number to extract
        cached_llm: LLM instance for text summarization

    Returns:
        Notice object with the extracted information
    """
    # Import detection functions to avoid circular imports
    from .utils import (
        detect_issn_num,
        detect_major_type_from_notice_number,
        detect_minor_pdf_type,
        detect_monthday_en_str,
        detect_monthday_num,
        detect_page_number,
        detect_year_num,
    )

    # Extract all the required fields from the PDF text
    pdf_monthday_num = detect_monthday_num(text)
    pdf_year_num = detect_year_num(text)
    pdf_issn_num = detect_issn_num(text)
    pdf_monthname_en_str = detect_monthday_en_str(text)
    pdf_type_major = detect_major_type_from_notice_number(notice_number)
    pdf_type_minor = detect_minor_pdf_type(text=text, pages=pages)
    pdf_page_num = detect_page_number(text)
    pdf_text = cached_llm.summarize(text)

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

    return notice
