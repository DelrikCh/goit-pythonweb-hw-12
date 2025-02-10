from cloudinary.utils import cloudinary_url
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import os

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def upload_image(url):
    """
    Uploads an image to Cloudinary and returns the secure URL.

    Args:
        url (str): The URL of the image to upload.
    """
    result = cloudinary.uploader.upload(url)
    return result["secure_url"]
