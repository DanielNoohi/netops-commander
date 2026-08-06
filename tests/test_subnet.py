"""Subnet calculator unit tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netops_commander.utils.subnet import describe_network


class SubnetTests(unittest.TestCase):
    def test_slash24(self):
        info = describe_network("192.168.1.0/24")
        self.assertEqual(info["network"], "192.168.1.0")
        self.assertEqual(info["broadcast"], "192.168.1.255")
        self.assertEqual(info["usable_hosts"], 254)
        self.assertEqual(info["first_usable"], "192.168.1.1")
        self.assertEqual(info["last_usable"], "192.168.1.254")
        self.assertTrue(info["is_private"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            describe_network("not-a-network")


if __name__ == "__main__":
    unittest.main()
