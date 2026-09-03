import ssl
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app


class WindowsCertificateFallbackTests(unittest.TestCase):
    def test_certificate_failure_uses_windows_trust_store_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "timetable.xlsx"
            cert_error = ssl.SSLCertVerificationError(1, "certificate verify failed")
            with patch.object(app, "_running_on_windows", return_value=True), \
                 patch.object(app, "_original_download_file", side_effect=cert_error), \
                 patch.object(app, "_download_with_windows_trust") as fallback:
                app.download_file("https://example.test/timetable.xlsx", destination)
            fallback.assert_called_once_with("https://example.test/timetable.xlsx", destination)

    def test_non_certificate_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "timetable.xlsx"
            with patch.object(app, "_running_on_windows", return_value=True), \
                 patch.object(app, "_original_download_file", side_effect=TimeoutError("network timeout")), \
                 patch.object(app, "_download_with_windows_trust") as fallback:
                with self.assertRaises(TimeoutError):
                    app.download_file("https://example.test/timetable.xlsx", destination)
            fallback.assert_not_called()

    def test_windows_fallback_keeps_tls_verification_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "timetable.xlsx"

            def fake_run(args, **kwargs):
                Path(kwargs["env"]["APU_SB_DOWNLOAD_OUT"]).write_bytes(b"x" * 1200)
                return subprocess.CompletedProcess(args, 0, "", "")

            with patch.object(app.subprocess, "run", side_effect=fake_run) as run:
                app._download_with_windows_trust("https://example.test/timetable.xlsx", destination)

            command = run.call_args.args[0][-1]
            self.assertIn("Invoke-WebRequest", command)
            self.assertNotIn("SkipCertificateCheck", command)
            self.assertNotIn("-k", command)
            self.assertEqual(destination.stat().st_size, 1200)

    def test_backend_uses_patched_download_function(self):
        self.assertIs(app._backend.download_file, app.download_file)


if __name__ == "__main__":
    unittest.main()
