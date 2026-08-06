"""Wake-on-LAN unit tests."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netops_commander.utils.wol import build_magic_packet, is_valid_mac, normalize_mac


class WolTests(unittest.TestCase):
    def test_normalize_formats(self):
        expected = bytes.fromhex("aabbccddeeff")
        self.assertEqual(normalize_mac("AA:BB:CC:DD:EE:FF"), expected)
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), expected)
        self.assertEqual(normalize_mac("aabb.ccddeeff"), expected)

    def test_magic_packet_structure(self):
        pkt = build_magic_packet("01:23:45:67:89:ab")
        self.assertEqual(len(pkt), 102)
        self.assertEqual(pkt[:6], b"\xff" * 6)
        self.assertEqual(pkt[6:12] * 16, pkt[6:])

    def test_invalid_mac(self):
        self.assertFalse(is_valid_mac("zz:zz:zz:zz:zz:zz"))
        self.assertFalse(is_valid_mac(""))


if __name__ == "__main__":
    unittest.main()
