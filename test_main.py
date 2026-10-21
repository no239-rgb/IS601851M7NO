import sys
import logging
import pytest
import runpy
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open



# Import application functions from main module
from main import (
    setup_logging,
    create_directory,
    is_valid_url,
    generate_qr_code,
    main,
)


class TestIsValidUrl:
    """Test URL validation logic across multiple URL patterns."""

    url_test_cases = {
        "valid_https": {"url": "https://github.com/kaw393939", "expected": True},
        "valid_http": {"url": "http://example.com", "expected": True},
        "valid_ftp": {"url": "ftp://example.com", "expected": True},  # FTP is valid in validators
        "valid_with_query_params": {
            "url": "https://sub.domain.org/path?user=1&ref=test",
            "expected": True,
        },
        "invalid_domain": {"url": "not-a-valid-url", "expected": False},
        "invalid_scheme": {"url": "http:/missing-slash.com", "expected": False},  # Malformed scheme
        "empty_string": {"url": "", "expected": False},
    }

    @pytest.mark.parametrize(
        "case_name, case_data", url_test_cases.items(), ids=url_test_cases.keys()
    )
    def test_is_valid_url(self, case_name: str, case_data: dict, caplog):
        """Verify URL validation accurately identifies valid and invalid URLs."""
        with caplog.at_level(logging.ERROR):
            result = is_valid_url(case_data["url"])
            assert result == case_data["expected"], f"Failed test case: {case_name}"
            
            if not case_data["expected"]:
                assert "Invalid URL provided" in caplog.text


class TestCreateDirectory:
    """Test directory creation helper and exception handling."""

    @patch.object(Path, "mkdir")
    def test_create_directory_success(self, mock_mkdir):
        """Test directory creation when path creation succeeds."""
        test_path = Path("/fake/directory")
        create_directory(test_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch.object(Path, "mkdir", side_effect=PermissionError("Access denied"))
    def test_create_directory_failure_exits(self, mock_mkdir, caplog):
        """Test directory creation failure logs error and terminates execution."""
        test_path = Path("/restricted/directory")
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                create_directory(test_path)
            
            assert exc_info.value.code == 1
            assert "Failed to create directory" in caplog.text


class TestGenerateQrCode:
    """Test QR code generation, color application, and error scenarios."""

    valid_generation_cases = {
        "default_colors": {
            "url": "https://github.com/kaw393939",
            "fill": "red",
            "back": "white",
        },
        "custom_colors": {
            "url": "https://example.com",
            "fill": "blue",
            "back": "yellow",
        },
        "monochrome": {
            "url": "https://python.org",
            "fill": "black",
            "back": "white",
        },
    }

    @pytest.mark.parametrize(
        "case_name, case", valid_generation_cases.items(), ids=valid_generation_cases.keys()
    )
    @patch("main.is_valid_url", return_value=True)
    @patch("main.qrcode.QRCode")
    def test_generate_qr_code_success(
        self, mock_qr_class, mock_valid_url, case_name: str, case: dict
    ):
        """Test successful QR code generation with parametrized color configurations."""
        mock_qr_instance = MagicMock()
        mock_qr_class.return_value = mock_qr_instance
        
        mock_path = MagicMock(spec=Path)
        mock_path.open = mock_open()

        generate_qr_code(
            data=case["url"],
            path=mock_path,
            fill_color=case["fill"],
            back_color=case["back"],
        )

        mock_valid_url.assert_called_once_with(case["url"])
        mock_qr_instance.add_data.assert_called_once_with(case["url"])
        mock_qr_instance.make.assert_called_once_with(fit=True)
        mock_qr_instance.make_image.assert_called_once_with(
            fill_color=case["fill"], back_color=case["back"]
        )

    @patch("main.is_valid_url", return_value=False)
    @patch("main.qrcode.QRCode")
    def test_generate_qr_code_invalid_url_aborts(self, mock_qr_class, mock_valid_url):
        """Test that generation exits early if URL validation fails."""
        mock_path = MagicMock(spec=Path)
        generate_qr_code("invalid-url", mock_path)
        
        mock_qr_class.assert_not_called()

    @patch("main.is_valid_url", return_value=True)
    @patch("main.qrcode.QRCode", side_effect=Exception("Image library error"))
    def test_generate_qr_code_exception_handled(self, mock_qr_class, mock_valid_url, caplog):
        """Test runtime exception catching during QR construction."""
        mock_path = MagicMock(spec=Path)
        with caplog.at_level(logging.ERROR):
            generate_qr_code("https://example.com", mock_path)
            assert "An error occurred while generating or saving the QR code" in caplog.text


class TestSetupLogging:
    """Test logging setup configuration."""

    @patch("logging.basicConfig")
    def test_setup_logging_configuration(self, mock_basic_config):
        """Verify basicConfig is invoked with stdout handler and INFO level."""
        setup_logging()
        mock_basic_config.assert_called_once()
        
        _, kwargs = mock_basic_config.call_args
        assert kwargs.get("level") == logging.INFO
        assert len(kwargs.get("handlers", [])) == 1
        assert isinstance(kwargs["handlers"][0], logging.StreamHandler)


class TestMainWorkflow:
    """Test full application execution flow through the main function."""

    cli_test_cases = {
        "default_args": {
            "args": [],
            "expected_url": "https://github.com/kaw393939",
        },
        "custom_url_flag": {
            "args": ["--url", "https://pytest.org"],
            "expected_url": "https://pytest.org",
        },
    }

    @pytest.mark.parametrize(
        "case_name, case", cli_test_cases.items(), ids=cli_test_cases.keys()
    )
    @patch("main.generate_qr_code")
    @patch("main.create_directory")
    @patch("main.setup_logging")
    def test_main_execution_flow(
        self,
        mock_setup_logging,
        mock_create_dir,
        mock_generate_qr,
        case_name: str,
        case: dict,
    ):
        """Test command-line execution and component orchestration."""
        with patch.object(sys, "argv", ["main.py"] + case["args"]):
            main()

            mock_setup_logging.assert_called_once()
            mock_create_dir.assert_called_once()
            mock_generate_qr.assert_called_once()

            # Verify the parsed URL is passed to the generation logic
            passed_url = mock_generate_qr.call_args[0][0]
            assert passed_url == case["expected_url"]

class TestMainEntryPoint:
    """Test the script entry point guard."""

    @patch("main.qrcode.QRCode")
    @patch.object(Path, "mkdir")
    @patch.object(Path, "open")
    def test_main_module_execution(self, mock_open_file, mock_mkdir, mock_qr):
        """Verify script execution under __main__ triggers full workflow."""
        with patch.object(sys, "argv", ["main.py"]):
            runpy.run_module("main", run_name="__main__")