import unittest

import torrt.utils as utils


class UtilsTestCase(unittest.TestCase):

    def test_base64encode(self):
        """base64encode should accept both bytes and string input
        and produce string output, regarding of python version

        base64encode usually used within RPC communications
        """

        string_to_encode = 'this is string'
        encoded_string = utils.base64encode(string_to_encode)

        self.assertIsInstance(encoded_string, str)

        bytes_to_encode = b'this is bytes to encode'
        encoded_bytes = utils.base64encode(bytes_to_encode)

        self.assertIsInstance(encoded_bytes, str)


if __name__ == '__main__':
    unittest.main()
