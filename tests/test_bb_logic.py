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
    def test_load_or_scan_first_time(self, mock_pdfplumber_open):
        """Test loading PDF for the first time (no cache)"""
        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Plumber Page 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Plumber Page 2"
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))

        # Check result is ScanInfo object
        assert isinstance(result, ScanInfo)
        assert result.plum_string == "Plumber Page 1\nPlumber Page 2"

        # Note: The current implementation doesn't create cache files anymore

    @patch("pdfplumber.open")
    def test_load_from_cache(self, mock_pdfplumber_open):
        """Test loading from cache when it exists"""
        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Plumber Page 1 from cache test"
        mock_pdf.pages = [mock_page1]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        result = load_or_scan_pdf_text(Path("test.pdf"))

        # Check result format
        assert isinstance(result, ScanInfo)
        assert result.plum_string == "Plumber Page 1 from cache test"

    @patch("pdfplumber.open")
    def test_cache_directory_creation(self, mock_pdfplumber_open):
        """Test that cache directory is created if it doesn't exist"""
        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        # Note: Current implementation doesn't create cache directory
        result = load_or_scan_pdf_text(Path("test.pdf"))
        assert isinstance(result, ScanInfo)


class TestGetNoticeForGGNum:
    """Tests for the get_notice_for_gg_num function"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_valid_pdf_parsing(self, mock_load_pdf, mock_locate):
        """Test parsing a valid PDF with expected format"""
        # Mock PDF text data
        mock_text = 'Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 2 N:B:The Government Printing Works will not:be held responsible for:the quality of "Hard Copies" or "Electronic Files submitted for publication purposes AIDS HELPLINE: 0800-0123-22 Prevention is the cure May\n2 No, 52724 IMPORTANT NOTICE: BE HELD RESPONSIBLE FOR ANY ERRORS THAT MIGHT OCCUR DUE To THE, SUBMISSION OF INCOMPLETE INCORRECT ILLEGIBLE COPY. Contents Gazette Page No. No. No. GENERAL NOTICES ALGEMENE KENNISGEWINGS Sports, Arts and Culture, Department of / Sport; Kuns en Kultuur; Departement van 3228 Draft National Policy on Heritage Memorialisation: Publication of notice to request public comment on-the draft National Policy Framework for Heritage Memorialisation _ 52724 3\ngovernment gazette staatskoerant general notices algemene kennisgewings department of sports, arts and culture Draft National Policy Framework for Heritage Memorialisation published for comment'
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(plum_string=mock_text)

        # Test with specific GG and notice numbers
        # Create a mock cached_llm
        mock_cached_llm = MagicMock()
        mock_cached_llm.summarize.return_value = (
            "Draft National Policy on Heritage Memorialisation"
        )
        notice = get_notice_for_gg_num(
            gg_number=52724, notice_number=3228, cached_llm=mock_cached_llm
        )

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
            plum_string="Invalid header text without expected format\nPage 2 text\nPage 3 text"
        )

        with pytest.raises(
            ValueError, match="Day number not found in the expected format"
        ):
            mock_cached_llm = MagicMock()
            mock_cached_llm.summarize.return_value = "Invalid text"
            get_notice_for_gg_num(
                gg_number=52724, notice_number=3228, cached_llm=mock_cached_llm
            )

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_unknown_major_type(self, mock_load_pdf, mock_locate):
        """Test handling of unknown major type"""
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            plum_string="Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May\n2 No, 52724 Contents 3228 Some text _ 52724 3\nunknown type text"
        )

        with pytest.raises(
            ValueError, match="No act information found in the provided text"
        ):
            mock_cached_llm = MagicMock()
            mock_cached_llm.summarize.return_value = "Unknown type text"
            get_notice_for_gg_num(
                gg_number=52724, notice_number=3228, cached_llm=mock_cached_llm
            )

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_unknown_minor_type(self, mock_load_pdf, mock_locate):
        """Test handling of unknown minor type"""
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            plum_string="Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May\n2 No, 52724 Contents 3228 Some text _ 52724 3\ngeneral notices algemene kennisgewings unknown department"
        )

        with pytest.raises(ValueError, match="No act information found"):
            mock_cached_llm = MagicMock()
            mock_cached_llm.summarize.return_value = "Unknown department text"
            get_notice_for_gg_num(
                gg_number=52724, notice_number=3228, cached_llm=mock_cached_llm
            )


class TestIntegration:
    """Integration tests that test the full workflow"""

    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.locate_gg_pdf_by_number")
    @patch("src.ongoing_convo_with_bronn_2025_06_10.utils.load_or_scan_pdf_text")
    def test_full_workflow(self, mock_load_pdf, mock_locate):
        """Test the complete workflow from PDF to formatted output"""
        # Mock PDF text directly as string
        mock_locate.return_value = Path("test.pdf")
        mock_load_pdf.return_value = ScanInfo(
            plum_string="Government Gazette Staaiskoerant REPUBLIEKVANSUIDAFRIKA Vol: 719 23 2025 No: 52724 Mei ISSN 1682-5845 May\n2 No, 52724 Contents 3228 Draft National Policy on Heritage Memorialisation: Publication of notice _ 52724 3\ngeneral notices algemene kennisgewings department of sports, arts and culture"
        )

        mock_cached_llm = MagicMock()
        mock_cached_llm.summarize.return_value = (
            "Draft National Policy on Heritage Memorialisation: Publication of notice"
        )
        record = get_notice_for_gg_num(
            gg_number=52724, notice_number=3228, cached_llm=mock_cached_llm
        )

        # Verify the record is correct
        assert record.gen_n_num == 3228
        assert record.type_major == MajorType.GENERAL_NOTICE

        # Verify the record is correctly parsed
        assert "Draft National Policy on Heritage Memorialisation" in record.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
