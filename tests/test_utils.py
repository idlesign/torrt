import pytest

import torrt.utils as utils


def test_base64encode_str():
    string_to_encode = 'this is string'
    encoded_string = utils.base64encode(string_to_encode)

    assert isinstance(encoded_string, str)
    assert encoded_string == "dGhpcyBpcyBzdHJpbmc=\n"

def test_base64encode_bytes():
    bytes_to_encode = b'this is bytes to encode'
    encoded_string = utils.base64encode(bytes_to_encode)

    assert isinstance(encoded_string, str)
    assert encoded_string == 'dGhpcyBpcyBieXRlcyB0byBlbmNvZGU=\n'


def test_iter_notifiers_stop_iteration():
    utils.NotifierObjectsRegistry._items = {}
    for _, notifier in utils.iter_notifiers():
        pass


def test_iter_rpc_stop_iteration():
    utils.RPCObjectsRegistry._items = {}
    for _, rpc_object in utils.iter_rpc():
        pass
