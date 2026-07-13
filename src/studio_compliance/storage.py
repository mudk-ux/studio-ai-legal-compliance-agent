"""GCS and local file access helpers. gs:// URIs and local paths are both accepted."""

from __future__ import annotations

import os
import posixpath
import tempfile


class StorageError(RuntimeError):
    pass


def is_gcs_uri(uri: str) -> bool:
    return uri.startswith("gs://")


def split_gcs_uri(uri: str) -> tuple[str, str]:
    if not is_gcs_uri(uri):
        raise StorageError(f"Not a gs:// URI: {uri}")
    rest = uri[len("gs://"):]
    bucket, _, blob = rest.partition("/")
    if not bucket or not blob:
        raise StorageError(f"Malformed gs:// URI: {uri}")
    return bucket, blob


def asset_basename(uri: str) -> str:
    if is_gcs_uri(uri):
        return posixpath.basename(split_gcs_uri(uri)[1])
    return os.path.basename(uri)


_CLIENT = None


def _client():
    """Cached GCS client. Client construction is expensive behind corporate
    cert proxies (~50s per instantiation observed live), so one
    client is shared for the process lifetime."""
    global _CLIENT
    if _CLIENT is None:
        from google.cloud import storage  # lazy: unit tests never need it

        _CLIENT = storage.Client()
    return _CLIENT


def read_text(uri: str, max_bytes: int | None = None) -> str:
    """Read a text asset from gs:// or a local path. Raises StorageError on any failure."""
    try:
        if is_gcs_uri(uri):
            bucket, blob = split_gcs_uri(uri)
            data = _client().bucket(bucket).blob(blob).download_as_bytes()
        else:
            with open(uri, "rb") as fh:
                data = fh.read()
    except Exception as exc:
        raise StorageError(f"Failed to read {uri}: {exc}") from exc
    if max_bytes is not None:
        data = data[:max_bytes]
    # Normalize newlines: CRLF payloads crash the Natural Language API's
    # response deserialization (observed live: "500 Exception deserializing
    # response!" on \r\n screenplay files).
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def read_bytes(uri: str) -> bytes:
    try:
        if is_gcs_uri(uri):
            bucket, blob = split_gcs_uri(uri)
            return _client().bucket(bucket).blob(blob).download_as_bytes()
        with open(uri, "rb") as fh:
            return fh.read()
    except Exception as exc:
        raise StorageError(f"Failed to read {uri}: {exc}") from exc


def upload_text(dest_uri: str, text: str, content_type: str = "application/json") -> str:
    """Write a string to an exact gs:// object URI. Raises StorageError on failure."""
    bucket_name, blob_name = split_gcs_uri(dest_uri)
    try:
        _client().bucket(bucket_name).blob(blob_name).upload_from_string(
            text, content_type=content_type
        )
    except Exception as exc:
        raise StorageError(f"Failed to write {dest_uri}: {exc}") from exc
    return dest_uri


def upload_file(local_path: str, dest_uri: str) -> str:
    """Upload a local file to gs://bucket/prefix/ or an exact gs:// object URI."""
    bucket_name, blob_name = split_gcs_uri(dest_uri)
    if dest_uri.endswith("/"):
        blob_name = posixpath.join(blob_name, os.path.basename(local_path))
    try:
        _client().bucket(bucket_name).blob(blob_name).upload_from_filename(local_path)
    except Exception as exc:
        raise StorageError(f"Failed to upload {local_path} -> {dest_uri}: {exc}") from exc
    return f"gs://{bucket_name}/{blob_name}"


def download_to_temp(uri: str) -> str:
    """Materialize a gs:// object locally; local paths are returned unchanged."""
    if not is_gcs_uri(uri):
        if not os.path.exists(uri):
            raise StorageError(f"Local file does not exist: {uri}")
        return uri
    bucket, blob = split_gcs_uri(uri)
    suffix = os.path.splitext(blob)[1]
    fd, local = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        _client().bucket(bucket).blob(blob).download_to_filename(local)
    except Exception as exc:
        raise StorageError(f"Failed to download {uri}: {exc}") from exc
    return local
