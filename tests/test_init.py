"""Tests for the __init__.py module"""

from src.ongoing_convo_with_bronn_2025_06_10 import hello


class TestInit:
    """Tests for the __init__.py module functions"""

    def test_hello_function(self):
        """Test the hello function returns expected string"""
        result = hello()
        assert result == "Hello from ongoing-convo-with-bronn-2025-06-10!"
        assert isinstance(result, str)
        assert len(result) > 0
