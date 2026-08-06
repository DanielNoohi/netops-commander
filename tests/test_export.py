"""HTML/CSV/JSON export helpers."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from netops_commander.utils.export import export_html, export_csv, export_json


class ExportTests(unittest.TestCase):
    def test_html_escapes_user_content(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out.html")
            rows = [{"ip": "1.2.3.4", "notes": "<script>alert(1)</script>"}]
            export_html(path, 'Title & "quotes"', rows)
            with open(path, encoding="utf-8") as f:
                body = f.read()
            self.assertNotIn("<script>", body)
            self.assertIn("&lt;script&gt;", body)
            self.assertIn("Title &amp; &quot;quotes&quot;", body)
            self.assertIn("1.2.3.4", body)

    def test_csv_and_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [{"a": 1, "b": "x"}]
            csv_path = os.path.join(td, "t.csv")
            json_path = os.path.join(td, "t.json")
            export_csv(csv_path, rows)
            export_json(json_path, rows)
            with open(csv_path, encoding="utf-8") as f:
                self.assertIn("a,b", f.read())
            with open(json_path, encoding="utf-8") as f:
                self.assertIn('"a": 1', f.read())


if __name__ == "__main__":
    unittest.main()
