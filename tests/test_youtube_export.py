import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "exporter", Path(__file__).resolve().parents[1] / "scripts/exporters/wordtower.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
URL = "https://www.youtube.com/watch?v=pTdvsfIMGes"


class YouTubeExportTests(unittest.TestCase):
    def test_rejects_plain_text_preview_before_submit(self):
        with tempfile.NamedTemporaryFile(suffix=".srt") as subtitles:
            with patch.object(exporter, "prepare_env", return_value={"configured": "yes"}), \
                 patch.object(exporter, "find_wordtower_request_script", return_value="request.py"), \
                 patch.object(exporter.subprocess, "run", return_value=SimpleNamespace(
                     returncode=0, stdout=json.dumps({"data": {"preview_id": "plain"}}))), \
                 patch.object(exporter, "submit_and_poll") as submit:
                with self.assertRaises(RuntimeError):
                    exporter.export_youtube(URL, subtitles.name)
                submit.assert_not_called()

    def test_timed_preview_preserves_youtube_command(self):
        preview = {"data": {"preview_id": "timed", "media_type": "youtube",
                            "source_url": URL, "subtitle_count": 260}}
        with tempfile.NamedTemporaryFile(suffix=".srt") as subtitles:
            with patch.object(exporter, "prepare_env", return_value={"configured": "yes"}), \
                 patch.object(exporter, "find_wordtower_request_script", return_value="request.py"), \
                 patch.object(exporter.subprocess, "run", return_value=SimpleNamespace(
                     returncode=0, stdout=json.dumps(preview))) as run, \
                 patch.object(exporter, "submit_and_poll") as submit:
                exporter.export_youtube(URL, subtitles.name)
                command = run.call_args.args[0]
                self.assertEqual(command[2:6], ["--youtube", URL, "--subtitles", subtitles.name])
                submit.assert_called_once_with("request.py", preview, "/imports/text",
                                               {"configured": "yes"}, preview_only=False)

    def test_rejects_empty_or_wrong_video_timeline(self):
        for count, url in [(0, URL), (True, URL), (260, URL + "x")]:
            with self.assertRaises(RuntimeError):
                exporter.validate_youtube_preview({"data": {"preview_id": "p",
                    "media_type": "youtube", "source_url": url, "subtitle_count": count}}, URL)

    def test_text_path_cannot_import_srt(self):
        with tempfile.NamedTemporaryFile(suffix=".srt") as subtitles:
            with patch.object(exporter, "prepare_env", return_value={"configured": "yes"}), \
                 patch.object(exporter, "find_wordtower_request_script", return_value="request.py"), \
                 patch.object(exporter.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    exporter.export_text(subtitles.name)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
