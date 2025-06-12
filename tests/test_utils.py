import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ongoing_convo_with_bronn_2025_06_10.utils import (
    Act,
    GgPdfs,
    MajorType,
    Notice,
    _extract_logical_lines,
    _parse_single_entry,
    attempt_to_get_pdf_page_num,
    decode_complex_pdf_type_minor,
    detect_gg_num,
    detect_issn_num,
    detect_major_type_from_notice_number,
    detect_minor_pdf_type,
    detect_monthday_en_str,
    detect_monthday_num,
    detect_page_number,
    detect_pdf_year_num,
    detect_year_num,
    get_notice_for_gg,
    load_or_scan_pdf_text,
    looks_like_a_year_string,
    looks_like_gg_num,
    looks_like_pdf_gen_n_num,
    looks_like_pdf_page_num,
    looks_like_pdf_with_long_list_of_notices,
    parse_gazette_document,
    parse_gg_filename,
)


class TestParseGgFilename:
    """Tests for parse_gg_filename function"""

    def test_valid_filename(self):
        """Test parsing a valid GG filename"""
        result = parse_gg_filename("gg52724_23May2025.pdf")
        assert result is not None
        assert result["gg_number"] == 52724
        assert result["publish_date"] == datetime(2025, 5, 23)

    def test_invalid_filename_format(self):
        """Test invalid filename format returns None"""
        assert parse_gg_filename("invalid_filename.pdf") is None
        assert parse_gg_filename("gg_23May2025.pdf") is None  # Missing number
        assert parse_gg_filename("52724_23May2025.pdf") is None  # Missing 'gg'

    def test_invalid_date_format(self):
        """Test invalid date format returns None"""
        assert parse_gg_filename("gg52724_32May2025.pdf") is None  # Invalid day
        assert parse_gg_filename("gg52724_23Xyz2025.pdf") is None  # Invalid month


class TestGgPdfs:
    """Tests for GgPdfs class"""

    def test_gg_pdfs_initialization(self):
        """Test GgPdfs initialization"""
        gg_pdfs = GgPdfs()
        assert gg_pdfs._path is None
        assert gg_pdfs._gg_number is None
        assert gg_pdfs._publish_date is None

    def test_add_valid_path(self):
        """Test adding a valid path"""
        gg_pdfs = GgPdfs()
        with tempfile.NamedTemporaryFile(
            suffix="_52724_23May2025.pdf", delete=False
        ) as f:
            test_path = Path(f.name)

        try:
            # Rename to have correct format
            correct_path = test_path.parent / "gg52724_23May2025.pdf"
            test_path.rename(correct_path)

            gg_pdfs.add_path(correct_path)
            assert gg_pdfs.path() == correct_path
        finally:
            if correct_path.exists():
                correct_path.unlink()

    def test_add_invalid_path(self):
        """Test adding invalid path raises assertion"""
        gg_pdfs = GgPdfs()
        with tempfile.NamedTemporaryFile(suffix="_invalid.pdf", delete=False) as f:
            test_path = Path(f.name)

        try:
            with pytest.raises(AssertionError):
                gg_pdfs.add_path(test_path)
        finally:
            test_path.unlink()

    def test_path_before_setting(self):
        """Test accessing path before setting raises assertion"""
        gg_pdfs = GgPdfs()
        with pytest.raises(AssertionError):
            gg_pdfs.path()


class TestLooksLikeFunctions:
    """Tests for various 'looks_like' functions"""

    def test_looks_like_a_year_string(self):
        """Test year string validation"""
        assert looks_like_a_year_string("2025") is True
        assert looks_like_a_year_string("1900") is True
        assert looks_like_a_year_string("2100") is True
        assert looks_like_a_year_string("1899") is False
        assert looks_like_a_year_string("2101") is False
        assert looks_like_a_year_string("202") is False  # Too short
        assert looks_like_a_year_string("20255") is False  # Too long
        assert looks_like_a_year_string("abcd") is False  # Not digits

    def test_looks_like_pdf_gen_n_num(self):
        """Test PDF gen number validation"""
        assert looks_like_pdf_gen_n_num(3228) is True
        assert looks_like_pdf_gen_n_num(2001) is True
        assert looks_like_pdf_gen_n_num(8999) is True
        assert looks_like_pdf_gen_n_num(1999) is False
        assert looks_like_pdf_gen_n_num(9001) is False

    def test_looks_like_gg_num(self):
        """Test GG number validation"""
        assert looks_like_gg_num(52724) is True
        assert looks_like_gg_num(30000) is True
        assert looks_like_gg_num(89999) is True
        assert looks_like_gg_num(29999) is False
        assert looks_like_gg_num(90001) is False

    def test_looks_like_pdf_page_num(self):
        """Test PDF page number validation"""
        assert looks_like_pdf_page_num(1) is True
        assert looks_like_pdf_page_num(50) is True
        assert looks_like_pdf_page_num(100) is True
        assert looks_like_pdf_page_num(0) is False
        assert looks_like_pdf_page_num(101) is False


class TestAttemptToGetPdfPageNum:
    """Tests for attempt_to_get_pdf_page_num function"""

    def test_valid_page_text(self):
        """Test extracting page number from valid text"""
        text = "staatskoerant; 23 mei-2025 no; 52726 3 government notices"
        result = attempt_to_get_pdf_page_num(52726, text)
        assert result == 3

    def test_invalid_gg_number(self):
        """Test assertion error with wrong GG number"""
        text = "staatskoerant; 23 mei-2025 no; 52726 3 government notices"
        with pytest.raises(AssertionError):
            attempt_to_get_pdf_page_num(99999, text)


class TestDetectMajorTypeFromNoticeNumber:
    """Tests for detect_major_type_from_notice_number function"""

    def test_board_notice_range(self):
        """Test board notice detection"""
        assert detect_major_type_from_notice_number(2500) == MajorType.BOARD_NOTICE
        assert detect_major_type_from_notice_number(500) == MajorType.BOARD_NOTICE

    def test_general_notice_range(self):
        """Test general notice detection"""
        assert detect_major_type_from_notice_number(3500) == MajorType.GENERAL_NOTICE

    def test_government_notice_range(self):
        """Test government notice detection"""
        assert detect_major_type_from_notice_number(6500) == MajorType.GOVERNMENT_NOTICE

    def test_unknown_range(self):
        """Test unknown range raises error"""
        with pytest.raises(ValueError, match="Unknown major type for notice number"):
            detect_major_type_from_notice_number(5000)


class TestDetectorFunctions:
    """Tests for various detector functions"""

    def test_detect_pdf_year_num(self):
        """Test PDF year detection"""
        text = "Some text with year 2025 in it"
        assert detect_pdf_year_num(text) == 2025

        with pytest.raises(ValueError, match="No 4-digit year between 2000 and 3000"):
            detect_pdf_year_num("No valid year here")

    def test_detect_gg_num(self):
        """Test GG number detection"""
        text = "Government Gazette No. 52724"
        assert detect_gg_num(text) == 52724

        with pytest.raises(ValueError, match="No 5-digit number starting with 5"):
            detect_gg_num("No valid GG number here")

    def test_detect_monthday_num(self):
        """Test month day detection"""
        text = "Vol. 719 23 2025"
        assert detect_monthday_num(text) == 23

        # Test with colon
        text_colon = "Vol: 719 15 2025"
        assert detect_monthday_num(text_colon) == 15

        # Test invalid day
        text_invalid = "Vol. 719 32 2025"
        with pytest.raises(ValueError, match="Invalid day number"):
            detect_monthday_num(text_invalid)

        # Test no match
        with pytest.raises(ValueError, match="Day number not found"):
            detect_monthday_num("No valid format here")

    def test_detect_year_num(self):
        """Test year detection"""
        text = "Vol. 719 23 2025"
        assert detect_year_num(text) == 2025

        # Test invalid year
        text_invalid = "Vol. 719 23 3500"
        with pytest.raises(ValueError, match="Invalid year number"):
            detect_year_num(text_invalid)

        # Test no match
        with pytest.raises(ValueError, match="Year number not found"):
            detect_year_num("No valid format here")

    def test_detect_issn_num(self):
        """Test ISSN detection"""
        text = "Government Gazette ISSN 1682-5845"
        assert detect_issn_num(text) == "1682-5845"

        with pytest.raises(ValueError, match="ISSN not found"):
            detect_issn_num("No ISSN here")

    def test_detect_monthday_en_str(self):
        """Test English month detection"""
        text = "Published in May 2025"
        assert detect_monthday_en_str(text) == "May"

        # Test case insensitive
        text_lower = "published in may 2025"
        assert detect_monthday_en_str(text_lower) == "May"

        with pytest.raises(ValueError, match="No valid English month name"):
            detect_monthday_en_str("No month here")

    def test_detect_page_number(self):
        """Test page number detection"""
        # Test first pattern
        text1 = "No. 52724 3"
        assert detect_page_number(text1) == 3

        # Test second pattern
        text2 = "_ 52724 5"
        assert detect_page_number(text2) == 5

        # Test invalid page number
        text_invalid = "No. 52724 0"
        with pytest.raises(ValueError, match="Invalid page number"):
            detect_page_number(text_invalid)

        # Test no match
        with pytest.raises(ValueError, match="Page number not found"):
            detect_page_number("No valid format here")


class TestLooksLikePdfWithLongListOfNotices:
    """Tests for looks_like_pdf_with_long_list_of_notices function"""

    def test_with_long_list(self):
        """Test text with long list of notices"""
        text = """Some header text
1234 First notice
5678 Second notice
9012 Third notice
More text"""
        assert looks_like_pdf_with_long_list_of_notices(text) is True

    def test_without_long_list(self):
        """Test text without long list"""
        text = """Some header text
1234 First notice
Some other text
5678 Second notice"""
        assert looks_like_pdf_with_long_list_of_notices(text) is False

    def test_empty_text(self):
        """Test empty text"""
        assert looks_like_pdf_with_long_list_of_notices("") is False


class TestDecodeComplexPdfTypeMinor:
    """Tests for decode_complex_pdf_type_minor function"""

    def test_standard_format(self):
        """Test standard act format parsing"""
        text = "Road Accident Fund Act (56/1996)"
        result = decode_complex_pdf_type_minor(text)
        assert result.whom == "Road Accident Fund"
        assert result.number == 56
        assert result.year == 1996

    def test_semicolon_format(self):
        """Test semicolon format parsing"""
        text = "Currency and Exchanges-Act; 1933 (Act No: 9 of 1933)"
        result = decode_complex_pdf_type_minor(text)
        assert result.whom == "Currency and Exchanges"
        assert result.number == 9
        assert result.year == 1933

    def test_no_format(self):
        """Test format without parentheses"""
        text = "Skills Development Act, No. 97 of 1998"
        result = decode_complex_pdf_type_minor(text)
        assert result.whom == "Skills Development"
        assert result.number == 97
        assert result.year == 1998

    def test_old_format(self):
        """Test old format"""
        text = "COMPETITION ACT, 1998 (ACT NO: 89 OF 1998)"
        result = decode_complex_pdf_type_minor(text)
        assert result.whom == "COMPETITION"
        assert result.number == 89
        assert result.year == 1998

    def test_special_case(self):
        """Test special case for Currency and Exchanges"""
        text = "with limited authority for the purpose of Exchange Control Regulations"
        result = decode_complex_pdf_type_minor(text)
        assert result.whom == "Currency and Exchanges"
        assert result.number == 9
        assert result.year == 1933

    def test_no_match(self):
        """Test when no pattern matches"""
        text = "Some random text without act information"
        with pytest.raises(ValueError, match="No act information found"):
            decode_complex_pdf_type_minor(text)


class TestDetectMinorPdfType:
    """Tests for detect_minor_pdf_type function"""

    def test_sports_department(self):
        """Test sports department detection"""
        text = "Department of Sports, Arts and Culture notice"
        result = detect_minor_pdf_type(text)
        assert result == "Department of Sports, Arts and Culture"

    def test_tourism_department(self):
        """Test tourism department detection"""
        text = "National Astro-Tourism initiative"
        result = detect_minor_pdf_type(text)
        assert result == "Department of Tourism"

    def test_transport_department(self):
        """Test transport department detection"""
        text = "Department of Transport regulations"
        result = detect_minor_pdf_type(text)
        assert result == "Department of Transport"

    def test_currency_exchange(self):
        """Test currency exchange detection"""
        text = "Authority for the purpose of Exchange Control"
        result = detect_minor_pdf_type(text)
        assert result == "CURRENCY AND EXCHANGES ACT 9 OF 1933"

    @patch(
        "src.ongoing_convo_with_bronn_2025_06_10.utils.decode_complex_pdf_type_minor"
    )
    def test_fallback_to_act_parsing(self, mock_decode):
        """Test fallback to act parsing"""
        mock_act = Mock()
        mock_act.whom = "Test Act"
        mock_act.number = 123
        mock_act.year = 2020
        mock_decode.return_value = mock_act

        text = "Some other act text"
        result = detect_minor_pdf_type(text)
        assert result == "Test Act ACT 123 of 2020"


class TestExtractLogicalLines:
    """Tests for _extract_logical_lines function"""

    def test_simple_extraction(self):
        """Test simple logical line extraction"""
        text = """1234 First line
continues here....... 52724 3
5678 Second line....... 52724 5"""
        result = _extract_logical_lines(text)
        assert len(result) == 2
        assert "First line continues here" in result[0]
        assert "Second line" in result[1]

    def test_single_line_entries(self):
        """Test single line entries"""
        text = "1234 Single line entry....... 52724 3"
        result = _extract_logical_lines(text)
        assert len(result) == 1
        assert "Single line entry" in result[0]


class TestParseSingleEntry:
    """Tests for _parse_single_entry function"""

    def test_standard_act_format(self):
        """Test parsing standard act format"""
        line = "1234 Road Accident Fund Act (56/1996): Notice text....... 52724 3"
        result = _parse_single_entry(line)

        assert result is not None
        assert result["notice_number"] == 1234
        assert result["law_description"] == "Road Accident Fund"
        assert result["law_number"] == 56
        assert result["law_year"] == 1996
        assert result["gazette_number"] == 52724
        assert result["page_number"] == 3

    def test_invalid_format(self):
        """Test invalid format handling"""
        line = "Invalid line format without proper structure"
        # This should trigger the assert 0 in the function
        with pytest.raises(AssertionError):
            _parse_single_entry(line)


class TestParseGazetteDocument:
    """Tests for parse_gazette_document function"""

    def test_full_document_parsing(self):
        """Test parsing a complete gazette document"""
        text = """Header text
1234 Road Accident Fund Act (56/1996): First notice....... 52724 3
5678 Skills Development Act (97/1998): Second notice....... 52724 5"""

        result = parse_gazette_document(text)
        assert len(result) == 2
        assert result[0]["notice_number"] == 1234
        assert result[1]["notice_number"] == 5678


class TestLoadOrScanPdfText:
    """Tests for load_or_scan_pdf_text function"""

    @patch("pdfplumber.open")
    def test_successful_text_extraction(self, mock_pdfplumber):
        """Test successful PDF text extraction"""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 text"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 text"
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))
        assert result == "Page 1 text\nPage 2 text"

    @patch("pdfplumber.open")
    def test_empty_pdf(self, mock_pdfplumber):
        """Test PDF with no extractable text"""
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))
        assert result == "[No plumber text extracted]"

    @patch("pdfplumber.open")
    def test_more_than_five_pages(self, mock_pdfplumber):
        """Test PDF with more than 5 pages (should only read first 5)"""
        mock_pdf = MagicMock()
        pages = []
        for i in range(10):  # 10 pages
            page = MagicMock()
            page.extract_text.return_value = f"Page {i + 1} text"
            pages.append(page)
        mock_pdf.pages = pages
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))
        # Should only have first 5 pages
        expected = "\n".join([f"Page {i + 1} text" for i in range(5)])
        assert result == expected


class TestGetNoticeForGg:
    """Tests for get_notice_for_gg function"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    @patch(
        "src.ongoing_convo_with_bronn_2025_06_10.utils.looks_like_pdf_with_long_list_of_notices"
    )
    def test_short_pdf_processing(self, mock_looks_like, mock_load_text):
        """Test processing a short PDF (not a long list)"""
        mock_looks_like.return_value = False
        mock_load_text.return_value = """Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May
Some content here
Department of Sports, Arts and Culture notice
No. 52724 3"""

        mock_cached_llm = MagicMock()
        mock_cached_llm.summarize.return_value = "Test summary"

        result = get_notice_for_gg(
            p=Path("test.pdf"),
            gg_number=52724,
            notice_number=3228,
            cached_llm=mock_cached_llm,
        )

        assert isinstance(result, Notice)
        assert result.gg_num == 52724
        assert result.gen_n_num == 3228

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    @patch(
        "src.ongoing_convo_with_bronn_2025_06_10.utils.looks_like_pdf_with_long_list_of_notices"
    )
    @patch(
        "src.ongoing_convo_with_bronn_2025_06_10.utils.get_notice_for_gg_from_pdf_text_with_long_list_of_notices"
    )
    def test_long_pdf_processing(
        self, mock_get_notice_long, mock_looks_like, mock_load_text
    ):
        """Test processing a long PDF (with long list)"""
        mock_looks_like.return_value = True
        mock_load_text.return_value = "Long PDF text"

        mock_notice = MagicMock()
        mock_get_notice_long.return_value = mock_notice

        mock_cached_llm = MagicMock()

        result = get_notice_for_gg(
            p=Path("test.pdf"),
            gg_number=52724,
            notice_number=3228,
            cached_llm=mock_cached_llm,
        )

        assert result == mock_notice
        mock_get_notice_long.assert_called_once()


class TestAct:
    """Tests for Act model"""

    def test_valid_act_creation(self):
        """Test creating a valid Act instance"""
        act = Act(whom="Road Accident Fund", year=1996, number=56)
        assert act.whom == "Road Accident Fund"
        assert act.year == 1996
        assert act.number == 56
