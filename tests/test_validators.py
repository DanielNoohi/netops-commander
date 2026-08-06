"""Validators unit tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netops_commander.utils.validators import (
    validate_cidr,
    validate_ip,
    validate_port_range,
    is_valid_host,
)


class ValidatorTests(unittest.TestCase):
    def test_cidr_ok(self):
        ok, msg = validate_cidr("10.0.0.0/24")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_cidr_too_large(self):
        ok, msg = validate_cidr("10.0.0.0/8")
        self.assertFalse(ok)

    def test_ip(self):
        self.assertTrue(validate_ip("127.0.0.1")[0])
        self.assertFalse(validate_ip("999.1.1.1")[0])

    def test_host(self):
        self.assertTrue(is_valid_host("example.com"))
        self.assertTrue(is_valid_host("192.168.0.1"))
        self.assertFalse(is_valid_host(""))

    def test_ports(self):
        ok, msg, ports = validate_port_range("22,80,443")
        self.assertTrue(ok)
        self.assertEqual(ports, [22, 80, 443])
        ok, msg, ports = validate_port_range("8000-8002")
        self.assertTrue(ok)
        self.assertEqual(ports, [8000, 8001, 8002])


if __name__ == "__main__":
    unittest.main()
