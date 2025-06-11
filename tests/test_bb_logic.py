import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError

from src.ongoing_convo_with_bronn_2025_06_10.utils import (
    MajorType,
    Notice,
    ScanInfo,
    get_notice_for_gg_num,
    load_or_scan_pdf_text,
)


class TestRecord:
    """Tests for the Record model"""

    def test_valid_record_creation(self):
        """Test creating a valid Record instance"""
        record = Notice(
            gen_n_num=3228,
            gg_num=52724,
            monthday_num=23,
            month_name="May",
            year=2025,
            page=3,
            issn_num="1682-5845",
            type_major=MajorType.GENERAL_NOTICE,
            type_minor="Department of Sports, Arts and Culture",
            text="Draft National Policy on Heritage Memorialisation",
        )
        assert record.gen_n_num == 3228
        assert record.gg_num == 52724
        assert record.monthday_num == 23
        assert record.month_name == "May"
        assert record.year == 2025
        assert record.page == 3
        assert record.issn_num == "1682-5845"
        assert record.type_major == MajorType.GENERAL_NOTICE
        assert record.type_minor == "Department of Sports, Arts and Culture"
        assert record.text == "Draft National Policy on Heritage Memorialisation"

    def test_invalid_record_missing_field(self):
        """Test that Record creation fails when required field is missing"""
        with pytest.raises(ValidationError):
            Notice(
                gen_n_num=3228,
                gg_num=52724,
                monthday_num=23,
                # missing month_name
                year=2025,
                page=3,
                issn_num="1682-5845",
                type_major=MajorType.GENERAL_NOTICE,
                type_minor="Department of Sports, Arts and Culture",
                text="Draft National Policy",
            )

    def test_invalid_record_wrong_type(self):
        """Test that Record creation fails with wrong field types"""
        with pytest.raises(ValidationError):
            Notice(
                gen_n_num="3228",  # Should be int
                gg_num=52724,
                monthday_num=23,
                month_name="May",
                year=2025,
                page=3,
                issn_num="1682-5845",
                type_major=MajorType.GENERAL_NOTICE,
                type_minor="Department of Sports, Arts and Culture",
                text="Draft National Policy",
            )

    def test_record_immutability(self):
        """Test that Record fields cannot be modified after creation"""
        record = Notice(
            gen_n_num=3228,
            gg_num=52724,
            monthday_num=23,
            month_name="May",
            year=2025,
            page=3,
            issn_num="1682-5845",
            type_major=MajorType.GENERAL_NOTICE,
            type_minor="Department of Sports, Arts and Culture",
            text="Draft National Policy",
        )
        with pytest.raises(ValidationError):
            record.gen_n_num = 9999


class TestMajorType:
    """Tests for the MajorType enum"""

    def test_general_notice_enum(self):
        """Test that GENERAL_NOTICE enum value is correct"""
        assert MajorType.GENERAL_NOTICE.value == "GENERAL_NOTICE"

    def test_enum_member_access(self):
        """Test accessing enum members"""
        assert MajorType["GENERAL_NOTICE"] == MajorType.GENERAL_NOTICE


class TestLoadOrScanPdfText:
    """Tests for the load_or_scan_pdf_text function"""

    def setup_method(self):
        """Create a temporary directory for test cache"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)

    @patch("pdfplumber.open")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.extract_pdf_text")
    def test_load_or_scan_first_time(self, mock_extract, mock_pdfplumber_open):
        """Test loading PDF for the first time (no cache)"""
        # Mock OCR results
        mock_extract.return_value = [
            (1, "Page 1 text", 0.95),
            (2, "Page 2 text", 0.98),
            (3, "Page 3 text", 0.99),
        ]

        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Plumber Page 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Plumber Page 2"
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))

        # Check that extract_pdf_text was called
        mock_extract.assert_called_once_with(Path("test.pdf"))

        # Check result is ScanInfo object
        assert isinstance(result, ScanInfo)
        assert result.ocr_string == "Page 1 text\nPage 2 text\nPage 3 text"
        assert result.plum_string == "Plumber Page 1\nPlumber Page 2"

        # Check cache was created
        assert os.path.exists("cache/test_ocr_cache.json")

        # Verify cache contents
        with open("cache/test_ocr_cache.json", "r") as f:
            cached_data = json.load(f)
        # JSON serializes tuples as lists, so we need to compare accordingly
        expected_data = [
            [page, text, conf] for page, text, conf in mock_extract.return_value
        ]
        assert cached_data == expected_data

    @patch("pdfplumber.open")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.extract_pdf_text")
    def test_load_from_cache(self, mock_extract, mock_pdfplumber_open):
        """Test loading from cache when it exists"""
        # Create cache directory and file
        os.makedirs("cache")
        cache_data = [
            (1, "Cached page 1", 0.95),
            (2, "Cached page 2", 0.98),
            (3, "Cached page 3", 0.99),
        ]
        with open("cache/test_ocr_cache.json", "w") as f:
            json.dump(cache_data, f)

        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Plumber Page 1 from cache test"
        mock_pdf.pages = [mock_page1]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))

        # Check that extract_pdf_text was NOT called
        mock_extract.assert_not_called()

        # Check result format
        assert isinstance(result, ScanInfo)
        assert result.ocr_string == "Cached page 1\nCached page 2\nCached page 3"
        assert result.plum_string == "Plumber Page 1 from cache test"

    @patch("pdfplumber.open")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.extract_pdf_text")
    def test_cache_directory_creation(self, mock_extract, mock_pdfplumber_open):
        """Test that cache directory is created if it doesn't exist"""
        mock_extract.return_value = [(1, "Text", 0.95)]

        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        # Ensure cache directory doesn't exist
        assert not os.path.exists("cache")

        load_or_scan_pdf_text(Path("test.pdf"))

        # Check cache directory was created
        assert os.path.exists("cache")


class TestGetNoticeForGGNum:
    """Tests for the get_notice_for_gg_num function"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_valid_pdf_parsing(self, mock_load_pdf, mock_locate):
        """Test parsing a valid PDF with expected format"""
        # Mock PDF text data
        mock_text = 'Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 2 N:B:The Government Printing Works will not:be held responsible for:the quality of "Hard Copies" or "Electronic Files submitted for publication purposes AIDS HELPLINE: 0800-0123-22 Prevention is the cure May\n2 No, 52724 IMPORTANT NOTICE: BE HELD RESPONSIBLE FOR ANY ERRORS THAT MIGHT OCCUR DUE To THE, SUBMISSION OF INCOMPLETE INCORRECT ILLEGIBLE COPY. Contents Gazette Page No. No. No. GENERAL NOTICES ALGEMENE KENNISGEWINGS Sports, Arts and Culture, Department of / Sport; Kuns en Kultuur; Departement van 3228 Draft National Policy on Heritage Memorialisation: Publication of notice to request public comment on-the draft National Policy Framework for Heritage Memorialisation _ 52724 3\ngovernment gazette staatskoerant general notices algemene kennisgewings department of sports, arts and culture Draft National Policy Framework for Heritage Memorialisation published for comment'
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            ocr_string=mock_text, plum_string="[No plumber text extracted]"
        )

        # Test with specific GG and notice numbers
        notice = get_notice_for_gg_num(gg_number=52724, notice_number=3228)

        # Verify record fields
        assert notice.gen_n_num == 3228
        assert notice.gg_num == 52724
        assert notice.monthday_num == 23
        assert notice.month_name == "May"
        assert notice.year == 2025
        assert notice.page == 3
        assert notice.issn_num == "1682-5845"
        assert notice.type_major == MajorType.GENERAL_NOTICE
        assert notice.type_minor == "Department of Sports, Arts and Culture"
        assert "Draft National Policy on Heritage Memorialisation" in notice.text

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_invalid_pdf_format_page1(self, mock_load_pdf, mock_locate):
        """Test handling of PDF with invalid format on page 1"""
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            ocr_string="Invalid header text without expected format\nPage 2 text\nPage 3 text",
            plum_string="[No plumber text extracted]",
        )

        with pytest.raises(
            AssertionError, match="Could not find header marker in PDF text"
        ):
            get_notice_for_gg_num(gg_number=52724, notice_number=3228)

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_unknown_major_type(self, mock_load_pdf, mock_locate):
        """Test handling of unknown major type"""
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            ocr_string="Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May\n2 No, 52724 Contents 3228 Some text _ 52724 3\nunknown type text",
            plum_string="[No plumber text extracted]",
        )

        with pytest.raises(
            ValueError, match="No act information found in the provided text"
        ):
            get_notice_for_gg_num(gg_number=52724, notice_number=3228)

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_unknown_minor_type(self, mock_load_pdf, mock_locate):
        """Test handling of unknown minor type"""
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            ocr_string="Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May\n2 No, 52724 Contents 3228 Some text _ 52724 3\ngeneral notices algemene kennisgewings unknown department",
            plum_string="[No plumber text extracted]",
        )

        with pytest.raises(ValueError, match="No act information found"):
            get_notice_for_gg_num(gg_number=52724, notice_number=3228)


class TestIntegration:
    """Integration tests that test the full workflow"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_full_workflow(self, mock_load_pdf, mock_locate):
        """Test the complete workflow from PDF to formatted output"""
        # Mock PDF text directly as string
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            ocr_string="Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May\n2 No, 52724 Contents 3228 Draft National Policy on Heritage Memorialisation: Publication of notice _ 52724 3\ngeneral notices algemene kennisgewings department of sports, arts and culture",
            plum_string="[No plumber text extracted]",
        )

        record = get_notice_for_gg_num(gg_number=52724, notice_number=3228)

        # Verify the record is correct
        assert record.gen_n_num == 3228
        assert record.type_major == MajorType.GENERAL_NOTICE

        # Verify the record is correctly parsed
        assert "Draft National Policy on Heritage Memorialisation" in record.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
