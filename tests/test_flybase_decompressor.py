"""Tests for double-gzip detection and decompression (Task 37.3)."""

from __future__ import annotations

import gzip
import io

import pytest

from hgnc_external_resource_updater.flybase_parser import (
    FlyBaseDecompressor,
)


def _gzip_compress(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(data)
    return buf.getvalue()


class TestFlyBaseDecompressor:
    """Test double-gzip detection and decompression."""

    def test_single_gzip_decompresses(self) -> None:
        original = b"group_id\tsym\tname\thgnc_id\nFBgg001\tSYM\tName\t123"
        compressed = _gzip_compress(original)

        result = FlyBaseDecompressor.decompress(compressed)
        assert result == original.decode("utf-8")

    def test_double_gzip_decompresses(self) -> None:
        original = b"FBgg001\tSYM\tName\t123\nFBgg002\tSYM2\tName2\t456"
        compressed_once = _gzip_compress(original)
        compressed_twice = _gzip_compress(compressed_once)

        result = FlyBaseDecompressor.decompress(compressed_twice)
        assert result == original.decode("utf-8")

    def test_plain_text_passes_through(self) -> None:
        text = b"hello world"
        result = FlyBaseDecompressor.decompress(text)
        assert result == "hello world"

    def test_invalid_gzip_raises_error(self) -> None:
        bad_data = b"\x1f\x8b" + b"\x00" * 100
        with pytest.raises(Exception):
            FlyBaseDecompressor.decompress(bad_data)

    def test_empty_input_returns_empty(self) -> None:
        result = FlyBaseDecompressor.decompress(b"")
        assert result == ""

    def test_is_gzip_detects_gzip(self) -> None:
        compressed = _gzip_compress(b"test")
        assert FlyBaseDecompressor.is_gzip(compressed) is True

    def test_is_gzip_detects_plain_text(self) -> None:
        assert FlyBaseDecompressor.is_gzip(b"plain text") is False

    def test_is_gzip_handles_short_input(self) -> None:
        assert FlyBaseDecompressor.is_gzip(b"\x1f") is False
        assert FlyBaseDecompressor.is_gzip(b"") is False
