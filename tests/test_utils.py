import torrt.utils as utils


def test_base64encode_str():
    string_to_encode = 'this is string'
    encoded_bytes = utils.base64encode(string_to_encode)

    assert isinstance(encoded_bytes, bytes)
    assert encoded_bytes == b'dGhpcyBpcyBzdHJpbmc=\n'


def test_base64encode_bytes():
    bytes_to_encode = b'this is bytes to encode'
    encoded_bytes = utils.base64encode(bytes_to_encode)

    assert isinstance(encoded_bytes, bytes)
    assert encoded_bytes == b'dGhpcyBpcyBieXRlcyB0byBlbmNvZGU=\n'
