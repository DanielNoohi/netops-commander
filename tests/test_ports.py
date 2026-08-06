"""Unit tests for utils/ports.py: open-port text format <-> list round-trip."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netops_commander.utils.ports import parse_open_ports, format_open_ports


class PortsTestCase(unittest.TestCase):
    def test_format_basic(self):
        self.assertEqual(format_open_ports([22, 80, 443]), "22, 80, 443")
        self.assertEqual(format_open_ports([22, 23, 24]), "22, 23, 24")
        self.assertEqual(format_open_ports([]), "")
        self.assertEqual(format_open_ports(None), "")

    def test_parse_round_trip(self):
        ports = [22, 80, 443, 3389]
        self.assertEqual(parse_open_ports(format_open_ports(ports)), ports)

    def test_parse_single_and_empty(self):
        self.assertEqual(parse_open_ports("22"), [22])
        self.assertEqual(parse_open_ports(""), [])
        self.assertEqual(parse_open_ports(None), [])

    def test_parse_non_numeric(self):
        self.assertEqual(parse_open_ports("22, 8a, 443"), [22, 443])
        self.assertEqual(parse_open_ports("foo"), [])


if __name__ == "__main__":
    unittest.main()