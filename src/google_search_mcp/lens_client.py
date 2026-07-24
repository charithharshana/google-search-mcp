import base64
import io
import ipaddress
import mimetypes
import os
import socket
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

LENS_CRUPLOAD_ENDPOINT = "https://lensfrontend-pa.googleapis.com/v1/crupload"
DEFAULT_LENS_API_KEY = "AIzaSyDr2UxVnv_U85AbhhY8XSHSIavUW0DC-sY"
LENS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1500


def _varint(value: int) -> bytes:
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        output.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(output)


def _field(number: int, value: bytes) -> bytes:
    return _varint(number << 3 | 2) + _varint(len(value)) + value


def _string(number: int, value: str) -> bytes:
    return _field(number, value.encode())


def _integer(number: int, value: int) -> bytes:
    return _varint(number << 3) + _varint(value)


def _message(number: int, value: bytes) -> bytes:
    return _field(number, value)


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            raise ValueError("Invalid protobuf varint")
    raise ValueError("Truncated protobuf varint")


def _parse_fields(data: bytes) -> list[tuple[int, int, int | bytes]]:
    fields = []
    offset = 0
    while offset < len(data):
        key, offset = _read_varint(data, offset)
        number, wire_type = key >> 3, key & 7
        if wire_type == 0:
            value, offset = _read_varint(data, offset)
        elif wire_type == 1:
            value = data[offset:offset + 8]
            offset += 8
        elif wire_type == 2:
            size, offset = _read_varint(data, offset)
            value = data[offset:offset + size]
            offset += size
        elif wire_type == 5:
            value = data[offset:offset + 4]
            offset += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type: {wire_type}")
        fields.append((number, wire_type, value))
    return fields


def _bytes_fields(data: bytes, number: int) -> list[bytes]:
    return [value for field, wire, value in _parse_fields(data) if field == number and wire == 2]


def _first_bytes(data: bytes, number: int) -> bytes | None:
    values = _bytes_fields(data, number)
    return values[0] if values else None


def _first_string(data: bytes, number: int) -> str:
    value = _first_bytes(data, number)
    return value.decode("utf-8", "replace") if value else ""


def _validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Image URL must use HTTP or HTTPS")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, None)}
    except socket.gaierror:
        addresses = set()
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Image URL must resolve to a public address")


class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        _validate_remote_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _load_source(image_source: str) -> tuple[bytes, str]:
    if image_source.startswith("data:image/"):
        header, encoded = image_source.split(",", 1)
        return base64.b64decode(encoded), header.split(";", 1)[0].split(":", 1)[1]

    if len(image_source) > 200 and "/" not in image_source[:50] and not image_source.startswith(("http", "~")):
        return base64.b64decode(image_source + "===", validate=True), "image/png"

    if image_source.startswith(("http://", "https://")):
        _validate_remote_url(image_source)
        request = urllib.request.Request(
            image_source,
            headers={
                "User-Agent": LENS_USER_AGENT,
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://lens.google.com/",
            },
        )
        opener = urllib.request.build_opener(_PublicRedirectHandler())
        with opener.open(request, timeout=30) as response:
            body = response.read(MAX_IMAGE_BYTES + 1)
            content_type = response.headers.get_content_type()
        if len(body) > MAX_IMAGE_BYTES:
            raise ValueError("Image is larger than 10 MB")
        return body, content_type

    path = Path(image_source).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {image_source}")
    body = path.read_bytes()
    if len(body) > MAX_IMAGE_BYTES:
        raise ValueError("Image is larger than 10 MB")
    return body, mimetypes.guess_type(path.name)[0] or "image/png"


def _prepare_image(image_bytes: bytes) -> tuple[bytes, int, int]:
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return image_bytes, 1, 1

    with Image.open(io.BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
        image = image.convert("RGBA")
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue(), image.width, image.height


def _build_request(image_bytes: bytes, width: int, height: int) -> bytes:
    request_id = (
        _integer(1, uuid.uuid4().int & ((1 << 63) - 1))
        + _integer(2, 1)
        + _integer(3, 1)
    )
    locale = _string(1, "en") + _string(2, "US") + _string(3, "America/New_York")
    client = _integer(1, 3) + _integer(2, 4) + _message(4, locale)
    request_context = _message(3, request_id) + _message(4, client)
    payload = _field(1, image_bytes)
    metadata = _integer(1, width) + _integer(2, height)
    image_data = _message(1, payload) + _message(3, metadata)
    objects_request = _message(1, request_context) + _message(3, image_data)
    return _message(1, objects_request)


def _parse_text(text_message: bytes) -> tuple[str, str]:
    text_layout = _first_bytes(text_message, 1)
    language = _first_string(text_message, 2)
    if not text_layout:
        return "", language

    paragraphs = []
    for paragraph in _bytes_fields(text_layout, 1):
        lines = []
        for line in _bytes_fields(paragraph, 2):
            words = []
            for word in _bytes_fields(line, 1):
                word_text = _first_string(word, 2)
                separator = _first_string(word, 3)
                words.append(word_text + separator)
            if words:
                lines.append("".join(words).strip())
        if lines:
            paragraphs.append("\n".join(lines))
    return "\n".join(paragraphs).strip(), language


def parse_response(data: bytes) -> dict[str, object]:
    objects_response = _first_bytes(data, 2)
    if not objects_response:
        return {"text": "", "language": "", "objects": []}

    text_message = _first_bytes(objects_response, 3)
    text, language = _parse_text(text_message) if text_message else ("", "")
    objects = []
    for overlay in _bytes_fields(objects_response, 2):
        object_id = _first_string(overlay, 1).lstrip("#")
        if object_id and object_id not in objects:
            objects.append(object_id)
    return {"text": text, "language": language, "objects": objects}


def _request(image_source: str) -> dict[str, object]:
    image_bytes, _ = _load_source(image_source)
    encoded, width, height = _prepare_image(image_bytes)
    api_key = os.environ.get("GOOGLE_LENS_API_KEY", DEFAULT_LENS_API_KEY)
    request = urllib.request.Request(
        f"{LENS_CRUPLOAD_ENDPOINT}",
        data=_build_request(encoded, width, height),
        headers={
            "Content-Type": "application/x-protobuf",
            "User-Agent": LENS_USER_AGENT,
            "Origin": "https://lens.google.com",
            "Referer": "https://lens.google.com/",
            "X-Goog-Api-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    return parse_response(body)


async def analyze_image(image_source: str) -> dict[str, object]:
    import asyncio

    return await asyncio.to_thread(_request, image_source)
