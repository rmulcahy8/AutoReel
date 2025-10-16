import tempfile
from pathlib import Path
from unittest import TestCase, mock

import autocaption


class DummyTemporaryDirectory:
    def __init__(self, path: str):
        self._path = path

    def __enter__(self):
        return self._path

    def __exit__(self, exc_type, exc, tb):
        return False


class GenerateCaptionsTest(TestCase):
    def test_pipeline_invokes_all_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "result.mp4"
            temp_dir = Path(tmpdir) / "work"
            temp_dir.mkdir()

            words = [
                {"text": "Hello", "start": 0.0, "end": 0.5},
                {"text": "world", "start": 0.5, "end": 1.0},
            ]

            with mock.patch("autocaption.tempfile.TemporaryDirectory", return_value=DummyTemporaryDirectory(str(temp_dir))), \
                mock.patch("autocaption.download_video", return_value=str(temp_dir / "video.mp4")) as download_mock, \
                mock.patch("autocaption.extract_audio", return_value=str(temp_dir / "audio.wav")) as extract_mock, \
                mock.patch("autocaption.transcribe_audio", return_value=words) as transcribe_mock, \
                mock.patch("autocaption.write_srt", return_value=str(temp_dir / "captions.srt")) as write_mock, \
                mock.patch("autocaption.burn_captions") as burn_mock:

                resolved_output = autocaption.generate_captions("https://youtu.be/example", str(output_path))

            self.assertEqual(resolved_output, str(output_path.resolve()))
            download_mock.assert_called_once()
            extract_mock.assert_called_once_with(
                str(temp_dir / "video.mp4"),
                str(temp_dir / "audio.wav"),
                ffmpeg_binary="ffmpeg",
            )
            transcribe_mock.assert_called_once()
            write_mock.assert_called_once()
            burn_mock.assert_called_once_with(
                str(temp_dir / "video.mp4"),
                str(temp_dir / "captions.srt"),
                str(output_path.resolve()),
                ffmpeg_binary="ffmpeg",
            )


class WriteSrtTest(TestCase):
    def test_write_srt_creates_expected_contents(self):
        words = [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "world", "start": 0.5, "end": 1.0},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = Path(tmpdir) / "captions.srt"
            autocaption.write_srt(words, str(srt_path))
            contents = srt_path.read_text(encoding="utf-8")

        expected = "1\n00:00:00,000 --> 00:00:00,500\nHello\n\n2\n00:00:00,500 --> 00:00:01,000\nworld\n\n"
        self.assertEqual(contents, expected)
