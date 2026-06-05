"""
Centralized Input Sanitization Module

Provides reusable sanitizers and validators for all SilverTrade API endpoints.
Every endpoint should use these functions instead of inline regex/string munging
to ensure consistent, auditable input processing.

Usage:
    from utils.input_sanitizer import sanitize_symbol, validate_exchange, sanitize_filename

    symbol = sanitize_symbol(request.json.get("symbol", ""))
    exchange = validate_exchange(request.json.get("exchange", ""))
    filename = sanitize_filename(request.json.get("filename", "export"))
"""

import os
import re
from typing import Optional

from utils.constants import VALID_EXCHANGES


# ---------------------------------------------------------------------------
# Symbol Sanitization
# ---------------------------------------------------------------------------

# Only allow standard trading symbol characters: letters, digits, hyphen (for
# option symbols like NIFTY28NOV2424000CE), colon (exchange:symbol format),
# dot, underscore, and slash.
_SYMBOL_ALLOWED = re.compile(r"^[A-Za-z0-9\-._:/]+$")

# Strip leading/trailing spaces and uppercase
_SYMBOL_MAX_LENGTH = 100


def sanitize_symbol(symbol: str, default: str = "") -> str:
    """Sanitize and normalize a trading symbol string.

    Args:
        symbol: Raw symbol string from user input.
        default: Fallback value if the symbol is invalid or empty.

    Returns:
        Uppercase, stripped symbol if valid; otherwise ``default``.
    """
    if not isinstance(symbol, str):
        return default

    cleaned = symbol.strip().upper()

    if not cleaned or len(cleaned) > _SYMBOL_MAX_LENGTH:
        return default

    if not _SYMBOL_ALLOWED.match(cleaned):
        return default

    return cleaned


# ---------------------------------------------------------------------------
# Exchange Validation
# ---------------------------------------------------------------------------


def validate_exchange(exchange: str, allow_none: bool = False) -> Optional[str]:
    """Validate and normalize an exchange code.

    Args:
        exchange: Raw exchange string from user input.
        allow_none: If True, returns None for empty/missing instead of empty string.

    Returns:
        Uppercase exchange string if valid; empty string (or None) otherwise.
    """
    if not isinstance(exchange, str):
        return None if allow_none else ""

    cleaned = exchange.strip().upper()

    if not cleaned:
        return None if allow_none else ""

    if cleaned in VALID_EXCHANGES:
        return cleaned

    return None if allow_none else ""


# ---------------------------------------------------------------------------
# Interval / Timeframe Sanitization
# ---------------------------------------------------------------------------

# Valid interval patterns: number + unit (m/h/D/W/M/Q/Y)
# Single-letter forms (D, W, M, Q, Y) are handled by the KNOWN set above.
# Unit letters m/h require a numeric prefix (e.g., 5m, 2h).
_INTERVAL_PATTERN = re.compile(r"^(\d+)([mhDWMQY])$")


def sanitize_interval(interval: str, default: str = "D") -> str:
    """Sanitize and validate a market data interval string.

    Args:
        interval: Raw interval string (e.g., "1m", "5m", "D", "W", "1h").
        default: Fallback interval if input is invalid.

    Returns:
        Validated interval string, or ``default``.
    """
    if not isinstance(interval, str):
        return default

    cleaned = interval.strip()

    if not cleaned:
        return default

    # Known safe intervals
    KNOWN = {"1m", "5m", "15m", "30m", "1h", "2h", "3h", "4h", "D", "W", "M", "Q", "Y"}
    if cleaned in KNOWN:
        return cleaned

    # Pattern match for custom intervals like 25m, 2h, 3D
    if _INTERVAL_PATTERN.match(cleaned):
        return cleaned

    return default


# ---------------------------------------------------------------------------
# Filename Sanitization (path-traversal prevention)
# ---------------------------------------------------------------------------


def sanitize_filename(name: str, default: str = "export") -> str:
    """Sanitize a filename to prevent path traversal and shell injection.

    Removes path separators, null bytes, and any character that is not
    alphanumeric, dash, underscore, or dot.

    Args:
        name: Raw filename string from user input.
        default: Fallback if the result is empty after sanitization.

    Returns:
        Safe filename string.
    """
    if not isinstance(name, str):
        return default

    # Remove path separators and null bytes
    safe = name.replace("/", "_").replace("\\", "_").replace("\x00", "")

    # Strip to safe characters only
    safe = re.sub(r"[^A-Za-z0-9_\-.]", "_", safe)

    # Limit length
    safe = safe[:255]

    # Prevent empty filenames and hidden files (starting with dot)
    if not safe or safe.startswith("."):
        return default

    return safe


# ---------------------------------------------------------------------------
# Date String Validation
# ---------------------------------------------------------------------------

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIMESTAMP_PATTERN = re.compile(r"^\d{10,13}$")


def validate_date_string(date_str: str) -> bool:
    """Validate a date string is in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate.

    Returns:
        True if the string matches YYYY-MM-DD format.
    """
    if not isinstance(date_str, str):
        return False
    return bool(_DATE_PATTERN.match(date_str.strip()))


def validate_timestamp_or_date(value: str) -> bool:
    """Validate a string is either YYYY-MM-DD or a numeric epoch timestamp.

    Args:
        value: String to validate.

    Returns:
        True if valid date or timestamp format.
    """
    if not isinstance(value, str):
        return False
    cleaned = value.strip()
    return bool(_DATE_PATTERN.match(cleaned)) or bool(_TIMESTAMP_PATTERN.match(cleaned))


# ---------------------------------------------------------------------------
# IP Address Validation
# ---------------------------------------------------------------------------


def validate_ip_address(ip_string: str) -> bool:
    """Validate that a string is a valid IPv4 or IPv6 address.

    Args:
        ip_string: IP address string to validate.

    Returns:
        True if valid IPv4 or IPv6 address.
    """
    try:
        import ipaddress
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Generic String Sanitizer (for display names, descriptions, etc.)
# ---------------------------------------------------------------------------

# Strip control characters (except tab, newline, carriage return)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str, max_length: int = 256, allow_newlines: bool = False) -> str:
    """Sanitize a free-text string by removing control characters and limiting length.

    Args:
        text: Raw string to sanitize.
        max_length: Maximum allowed length (default 256).
        allow_newlines: If True, preserves \\n; otherwise strips it.

    Returns:
        Sanitized text string.
    """
    if not isinstance(text, str):
        return ""

    # Remove null bytes and control characters
    cleaned = _CONTROL_CHARS.sub("", text)

    if not allow_newlines:
        cleaned = cleaned.replace("\n", " ").replace("\r", " ")

    # Remove excessive whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


# ---------------------------------------------------------------------------
# SQL Identifier Sanitizer (table names, column names)
# ---------------------------------------------------------------------------

# Only allow alphanumeric and underscore for SQL identifiers
_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize_sql_identifier(name: str) -> Optional[str]:
    """Sanitize a SQL identifier (table/column name) for safe use in queries.

    Only allows alphanumeric characters and underscores. Returns None if the
    string is not a valid SQL identifier. Use this when you MUST interpolate
    an identifier into a SQL string (e.g., dynamic table names).

    Args:
        name: Raw identifier string.

    Returns:
        Safe identifier string, or None if invalid.
    """
    if not isinstance(name, str):
        return None

    cleaned = name.strip()

    if not cleaned or len(cleaned) > 128:
        return None

    if _SQL_IDENTIFIER.match(cleaned):
        return cleaned

    return None


# ---------------------------------------------------------------------------
# Compression codec validation (defense-in-depth for Parquet export)
# ---------------------------------------------------------------------------

VALID_COMPRESSION_CODECS = {"zstd", "snappy", "gzip", "none"}


def validate_compression_codec(codec: str, default: str = "zstd") -> str:
    """Validate a compression codec against the allowed set.

    Args:
        codec: Compression codec string (e.g., "zstd", "snappy", "gzip", "none").
        default: Fallback if codec is not recognized (default "zstd").

    Returns:
        Validated codec string, or ``default``.
    """
    if not isinstance(codec, str):
        return default
    cleaned = codec.strip().lower()
    if cleaned in VALID_COMPRESSION_CODECS:
        return cleaned
    return default
