"""Cross-version compatibility library

This module contains various version-bound function implementations.

"""
import base64


def encode_value(value, encoding=None):
    """Encodes a value.

    :param str|unicode value:
    :param str|unicode encoding: Encoding charset.
    :rtype: bytes

    """
    if encoding is None:
        return value

    return value.encode(encoding)


def base64encode(string_or_bytes):
    """Return base64 encoded input

    :param string_or_bytes:
    :return: bytes
    """
    if isinstance(string_or_bytes, str):
        string_or_bytes = string_or_bytes.encode('utf-8')

    return base64.encodebytes(string_or_bytes).decode('ascii').encode('utf-8')
