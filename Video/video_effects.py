"""Local MP4 probing, frame processing and H.264/AAC export."""

from dataclasses import dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Timer

from PIL import Image

from Images import Image_filters as filters
from Images.image_histogram import adjust_brightness


MAX_BYTES = 20 * 1024 * 1024
MAX_SECONDS = 30
LOCAL_MP4 = ["-protocol_whitelist", "file,pipe", "-f", "mov"]
EFFECTS = {
    "Grayscale": filters.grayscale_average,
    "Invert Colours": filters.negative,
    "Posterization": filters.posterize_n_levels,
    "Brightness": adjust_brightness,
}


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: Fraction
    duration: float
    stream: int
    audio_stream: int | None


# Video tools: Locate the platform's local binaries without invoking a shell.
def video_tools_available():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


# Probe MP4: Find the primary moving-picture stream, duration and first audio stream.
def _probe(path):
    if not video_tools_available():
        raise ValueError("Video needs FFmpeg and ffprobe on your computer's PATH.")
    try:
        command = ["ffprobe", "-v", "error", *LOCAL_MP4, "-show_streams", "-show_format",
                   "-of", "json", str(path)]
        report = json.loads(subprocess.check_output(command, timeout=12, stderr=subprocess.PIPE))
        streams = report["streams"]
        video = next(s for s in streams if s["codec_type"] == "video"
                     and not s.get("disposition", {}).get("attached_pic"))
        audio = next((s["index"] for s in streams if s["codec_type"] == "audio"), None)
        fps = Fraction(video.get("avg_frame_rate", "0/1").replace("0/0", "0/1"))
        if not fps:
            fps = Fraction(video["r_frame_rate"])
        seconds = video.get("duration")
        duration = float(report["format"]["duration"] if seconds in (None, "N/A") else seconds)
        width, height = video["width"], video["height"]
        rotation = next((s["rotation"] for s in video.get("side_data_list", []) if "rotation" in s), 0)
        if round(rotation) % 180 == 90:
            width, height = height, width
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, StopIteration, ZeroDivisionError) as exc:
        raise ValueError("Choose an MP4 with a readable video stream.") from exc

    # Allow small container rounding around the 30-second boundary.
    if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS + 0.05:
        raise ValueError("Choose an MP4 clip up to 30 seconds.")
    if not 0 < fps <= 60 or min(width, height) < 2 or max(width, height) > 1920 or width * height > 1920 * 1080:
        raise ValueError("Use an MP4 up to 1080p and 60 frames per second.")
    return VideoInfo(width, height, fps, duration, video["index"], audio)


# Input metadata: Probe a bounded upload in a private temporary folder.
def get_video_info(payload):
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Choose an MP4 file up to 20 MB.")
    with TemporaryDirectory(prefix="medialab-video-") as folder:
        path = Path(folder) / "input.mp4"
        path.write_bytes(payload)
        return _probe(path)


# Frame effect: Apply the same functions used by the Image workbench.
def _effect(image, effect, value):
    return image if effect == "Trim" else EFFECTS[effect](image, *(() if value is None else (value,)))


# Decode command: Read equally spaced RGB frames at the clip's measured frame rate.
def _decoder(path, info, start, duration, frame_limit):
    return [
        "ffmpeg", "-v", "error", "-nostdin", "-filter_threads", "1", "-ss", str(start),
        *LOCAL_MP4, "-i", str(path), "-map", f"0:{info.stream}", "-an", "-sn",
        "-t", str(duration), "-vf", f"fps={info.fps},scale={info.width}:{info.height},setsar=1",
        "-frames:v", str(frame_limit), "-pix_fmt", "rgb24", "-threads", "1", "-f", "rawvideo", "pipe:1",
    ]


# Preview frame: Show the result at the chosen start without rendering an entire clip.
def preview_frame(payload, info, effect, value=None, *, start=0):
    if effect not in (*EFFECTS, "Trim") or not 0 <= start < info.duration:
        raise ValueError("Choose an effect and a start time within the clip.")
    with TemporaryDirectory(prefix="medialab-frame-") as folder:
        path = Path(folder) / "input.mp4"
        path.write_bytes(payload)
        try:
            data = subprocess.check_output(
                _decoder(path, info, start, info.duration - start, 1), timeout=15, stderr=subprocess.PIPE,
            )
            frame = Image.frombytes("RGB", (info.width, info.height), data)
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            raise ValueError("MediaLab could not read a frame at that position.") from exc
    return _effect(frame, effect, value)


# Process MP4: Stream frames through the Pillow effect, then encode for browser playback.
def process_video(payload, info, effect, value=None, *, start=0, end=None, progress=None):
    end = info.duration if end is None else end
    if effect not in (*EFFECTS, "Trim") or not 0 <= start < end <= info.duration:
        raise ValueError("Choose an effect and an end time after the start.")
    duration = end - start
    frame_count = math.ceil(duration * info.fps)
    frame_bytes = info.width * info.height * 3
    with TemporaryDirectory(prefix="medialab-video-") as folder:
        source = Path(folder) / "input.mp4"
        target = Path(folder) / "edited.mp4"
        source.write_bytes(payload)
        encode = [
            "ffmpeg", "-v", "error", "-nostdin", "-filter_threads", "1",
            "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{info.width}x{info.height}", "-framerate", str(info.fps), "-i", "pipe:0",
        ]
        if info.audio_stream is not None:
            encode += ["-ss", str(start), "-t", str(duration), *LOCAL_MP4, "-i", str(source),
                       "-map", "0:v:0", "-map", f"1:{info.audio_stream}", "-c:a", "aac",
                       "-b:a", "128k", "-af", "apad", "-shortest"]
        encode += ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264",
                   "-preset", "ultrafast", "-threads", "2", "-crf", "25", "-maxrate", "4M",
                   "-bufsize", "4M", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                   "-t", str(duration), str(target)]
        try:
            with (Path(folder) / "ffmpeg.log").open("wb") as errors:
                with subprocess.Popen(_decoder(source, info, start, duration, frame_count),
                                      stdout=subprocess.PIPE, stderr=errors) as decoder:
                    try:
                        with subprocess.Popen(encode, stdin=subprocess.PIPE, stderr=errors) as encoder:
                            def stop_processes():
                                for process in (decoder, encoder):
                                    if process.poll() is None:
                                        process.kill()

                            watchdog = Timer(150, stop_processes)
                            watchdog.daemon = True
                            watchdog.start()
                            try:
                                processed = 0
                                for index in range(frame_count):
                                    raw = decoder.stdout.read(frame_bytes)
                                    if not raw:
                                        break
                                    if len(raw) != frame_bytes:
                                        raise ValueError("The source video ended mid-frame.")
                                    frame = Image.frombytes("RGB", (info.width, info.height), raw)
                                    encoder.stdin.write(_effect(frame, effect, value).tobytes())
                                    processed += 1
                                    if progress and (index % 10 == 0 or processed == frame_count):
                                        progress(min(95, round(95 * processed / frame_count)))
                                encoder.stdin.close()
                                if decoder.wait(timeout=12) or encoder.wait(timeout=25) or not processed:
                                    raise ValueError("Video processing failed. Check the MP4 and your FFmpeg H.264/AAC support.")
                            finally:
                                watchdog.cancel()
                                stop_processes()
                    finally:
                        if decoder.poll() is None:
                            decoder.kill()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("Video processing could not finish. Check FFmpeg H.264/AAC support or try a shorter MP4.") from exc
        try:
            if target.stat().st_size > MAX_BYTES:
                raise ValueError("The export is too large. Trim the clip first.")
            return target.read_bytes(), _probe(target)
        except OSError as exc:
            raise ValueError("FFmpeg could not create an MP4 export.") from exc
