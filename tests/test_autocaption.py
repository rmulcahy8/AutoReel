import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
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
            shorts_dir = str(Path(tmpdir) / "shorts")

            words = [
                {"text": "Hello", "start": 0.0, "end": 0.5},
                {"text": "world", "start": 0.5, "end": 1.0},
            ]

            with mock.patch(
                "autocaption.tempfile.TemporaryDirectory",
                return_value=DummyTemporaryDirectory(str(temp_dir)),
            ), mock.patch(
                "autocaption.download_video", return_value=str(temp_dir / "video.mp4")
            ) as download_mock, mock.patch(
                "autocaption.extract_audio", return_value=str(temp_dir / "audio.wav")
            ) as extract_mock, mock.patch(
                "autocaption.transcribe_audio", return_value=words
            ) as transcribe_mock, mock.patch(
                "autocaption.write_srt", return_value=str(temp_dir / "captions.srt")
            ) as write_mock, mock.patch("autocaption.burn_captions") as burn_mock, mock.patch(
                "autocaption.select_highlight_segments", return_value=[(0.0, 1.0)]
            ) as select_mock, mock.patch("autocaption.create_shorts") as create_shorts_mock:

                resolved_output = autocaption.generate_captions(
                    "https://youtu.be/example",
                    str(output_path),
                    shorts_dir=shorts_dir,
                )

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
            select_mock.assert_called_once()
            create_shorts_mock.assert_called_once_with(
                str(output_path.resolve()),
                [(0.0, 1.0)],
                shorts_dir,
                ffmpeg_binary="ffmpeg",
            )


class SelectHighlightSegmentsTest(TestCase):
    def test_select_highlight_segments_parses_openai_response(self):
        words = [
            {"text": "This", "start": 0.0, "end": 0.5},
            {"text": "is", "start": 0.5, "end": 0.8},
            {"text": "great.", "start": 0.8, "end": 1.5},
            {"text": "Another", "start": 5.0, "end": 5.4},
            {"text": "moment.", "start": 5.4, "end": 6.0},
        ]

        mock_client = mock.Mock()
        response_text = "1) 0-2\n2) 5-8\n3) 10-12\n4) 15-18\n5) 20-24"
        mock_response = SimpleNamespace(
            output=[SimpleNamespace(content=[SimpleNamespace(text=response_text)])]
        )
        mock_client.responses.create.return_value = mock_response

        spans = autocaption.select_highlight_segments(
            words,
            prompt="Pick",  # ensure custom prompt is used
            client=mock_client,
        )

        expected_segments = "\n".join(
            [
                "[1] 0.00-1.50: This is great.",
                "[2] 5.00-6.00: Another moment.",
            ]
        )
        expected_user_text = f"Pick\n\nSegments:\n{expected_segments}"

        mock_client.responses.create.assert_called_once_with(
            model="gpt-5-nano",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": expected_user_text,
                        }
                    ],
                }
            ],
        )
        self.assertEqual(
            spans,
            [(0.0, 2.0), (5.0, 8.0), (10.0, 12.0), (15.0, 18.0), (20.0, 24.0)],
        )


class CreateShortsTest(TestCase):
    def test_create_shorts_invokes_ffmpeg_for_each_span(self):
        spans = [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0), (15.0, 20.0), (20.0, 25.0)]

        with tempfile.TemporaryDirectory() as tmpdir:
            captioned_video_path = str(Path(tmpdir) / "video.mp4")
            shorts_dir = str(Path(tmpdir) / "shorts")

            with mock.patch("autocaption.subprocess.run") as run_mock:
                outputs = autocaption.create_shorts(
                    captioned_video_path,
                    spans,
                    shorts_dir,
                    ffmpeg_binary="/usr/bin/ffmpeg",
                )

        self.assertEqual(len(outputs), 5)
        self.assertTrue(all(output.startswith(shorts_dir) for output in outputs))
        expected_calls = []
        for index, (start, end) in enumerate(spans, start=1):
            expected_end = min(end, start + 60.0)
            clip_path = Path(shorts_dir) / f"short_{index}.mp4"
            expected_calls.append(
                mock.call(
                    [
                        "/usr/bin/ffmpeg",
                        "-y",
                        "-i",
                        captioned_video_path,
                        "-ss",
                        f"{start:.3f}",
                        "-to",
                        f"{expected_end:.3f}",
                        "-c",
                        "copy",
                        str(clip_path),
                    ],
                    check=True,
                )
            )

        run_mock.assert_has_calls(expected_calls)
        self.assertEqual(run_mock.call_count, 5)

    def test_create_shorts_trims_spans_exceeding_one_minute(self):
        spans = [(30.0, 200.0)]

        with tempfile.TemporaryDirectory() as tmpdir:
            captioned_video_path = str(Path(tmpdir) / "video.mp4")
            shorts_dir = str(Path(tmpdir) / "shorts")

            with mock.patch("autocaption.subprocess.run") as run_mock:
                outputs = autocaption.create_shorts(
                    captioned_video_path,
                    spans,
                    shorts_dir,
                    ffmpeg_binary="ffmpeg",
                )

        self.assertEqual(len(outputs), 1)
        expected_clip = Path(shorts_dir) / "short_1.mp4"
        run_mock.assert_called_once_with(
            [
                "ffmpeg",
                "-y",
                "-i",
                captioned_video_path,
                "-ss",
                "30.000",
                "-to",
                "90.000",
                "-c",
                "copy",
                str(expected_clip),
            ],
            check=True,
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


class TranscribeAudioTest(TestCase):
    def test_transcribe_audio_uses_supported_arguments(self):
        mock_model = object()
        mock_transcription = {
            "segments": [
                {
                    "words": [
                        {"text": " Hello", "start": 0.0, "end": 0.5},
                        {"text": "world ", "start": 0.5, "end": 1.0},
                    ]
                }
            ]
        }

        whisper_mock = mock.Mock()
        whisper_mock.load_model.return_value = mock_model
        whisper_mock.transcribe.return_value = mock_transcription

        with mock.patch.dict(sys.modules, {"whisper_timestamped": whisper_mock}):
            words = autocaption.transcribe_audio(
                "audio.wav", model_name="small", language="en", device="cuda"
            )

        whisper_mock.load_model.assert_called_once_with("small", device="cuda")
        whisper_mock.transcribe.assert_called_once_with(
            mock_model,
            audio="audio.wav",
            language="en",
            task="transcribe",
        )
        expected_words = [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "world", "start": 0.5, "end": 1.0},
        ]
        self.assertEqual(words, expected_words)
