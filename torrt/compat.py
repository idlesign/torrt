# -*- coding: utf-8 -*-
"""Cross-version compatability library

This module contains various version-bound function implementations.

Todo:
    * Split this module into multiple files, if it's length exceeds 100 LOC

"""
import six
import base64


def encode_value(value, encoding=None):
    """Encodes a value.

    :param str|unicode value:
    :param str|unicode encoding: Encoding charset.
    :rtype: bytes

    """
    if encoding is None:
        return value

    if six.PY2:
        value = unicode(value, 'UTF-8')

    return value.encode(encoding)


if six.PY3:

    def base64encode(string_or_bytes):
        """Return base64 encoded input

        :param string_or_bytes:
        :return: str
        """
        if isinstance(string_or_bytes, str):
            string_or_bytes = string_or_bytes.encode('utf-8')

        return base64.encodebytes(string_or_bytes).decode('ascii')

else:

    def base64encode(string_or_bytes):
        """Return base64 encoded input

        :param string_or_bytes:
        :return: str
        """
        return base64.encodestring(string_or_bytes)
