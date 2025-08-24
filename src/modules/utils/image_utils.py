import base64
from io import BytesIO

from PIL import Image


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Converts a PIL Image to a base64 encoded string."""
    buffered = BytesIO()
    image.save(buffered, format=format)
    img_byte = buffered.getvalue()
    return base64.b64encode(img_byte).decode("utf-8")
