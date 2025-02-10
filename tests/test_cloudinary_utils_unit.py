import pytest
from app.cloudinary_utils import upload_image
from unittest.mock import patch


@pytest.fixture
def mock_cloudinary_response():
    return {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1234567890/sample.jpg"
    }


@patch("cloudinary.uploader.upload")
def test_upload_image_success(mock_upload, mock_cloudinary_response):
    mock_upload.return_value = mock_cloudinary_response
    url = "https://example.com/sample.jpg"
    result = upload_image(url)
    assert result == mock_cloudinary_response["secure_url"]
    mock_upload.assert_called_once_with(url)


@patch("cloudinary.uploader.upload")
def test_upload_image_failure(mock_upload):
    mock_upload.side_effect = Exception("Upload failed")
    url = "https://example.com/sample.jpg"
    with pytest.raises(Exception, match="Upload failed"):
        upload_image(url)
    mock_upload.assert_called_once_with(url)
