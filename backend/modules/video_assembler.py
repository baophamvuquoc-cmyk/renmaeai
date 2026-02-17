"""
Video Assembler — Cut footage to audio duration, combine, and render.

Uses MoviePy to:
1. Cut/loop footage to match audio duration
2. Burn subtitles (TextClip) onto each scene
3. Combine footage + audio → scene video
4. Add crossfade transitions between scenes
5. Mix background music at configurable volume
6. Export at configurable quality (480p/720p/1080p)

Adapted from SamurAIGPT/Text-To-Video-AI render_engine.py.
"""

import gc
import os
import tempfile
import platform
import subprocess
from typing import List, Dict, Optional, Tuple
from pathlib import Path


# ── Quality presets ──
QUALITY_PRESETS = {
    "480p":  {"height": 480,  "bitrate": "1500k", "preset": "veryfast"},
    "720p":  {"height": 720,  "bitrate": "3000k", "preset": "veryfast"},
    "1080p": {"height": 1080, "bitrate": "5000k", "preset": "medium"},
}


class VideoAssembler:
    """Video assembly: cut footage to audio duration, combine, and export."""

    def __init__(self, output_dir: str = "video_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Find ffmpeg path
        self.ffmpeg_path = "ffmpeg"  # default

        # Setup ffmpeg paths (bundled or system)
        try:
            from modules.ffmpeg_setup import get_ffmpeg_path, get_ffprobe_path
            ffmpeg_path = get_ffmpeg_path()
            ffprobe_path = get_ffprobe_path()

            # Tell MoviePy where ffmpeg is
            os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_path
            self.ffmpeg_path = ffmpeg_path
            print(f"[VideoAssembler] Using ffmpeg: {ffmpeg_path}")
        except ImportError:
            ffprobe_path = None
            # Try to find ffmpeg in PATH
            found = self._find_program("ffmpeg")
            if found:
                self.ffmpeg_path = found

        # Check for ImageMagick (needed for text overlays / subtitles)
        magick_path = self._find_program("magick")
        if magick_path:
            os.environ['IMAGEMAGICK_BINARY'] = magick_path
            self.has_imagemagick = True
            print(f"[VideoAssembler] ImageMagick found: {magick_path}")
        else:
            self.has_imagemagick = False
            print("[VideoAssembler] ImageMagick not found -- subtitles will be skipped")

    @staticmethod
    def _find_program(program_name: str) -> Optional[str]:
        """Find program path (cross-platform)."""
        try:
            search_cmd = "where" if platform.system() == "Windows" else "which"
            return subprocess.check_output(
                [search_cmd, program_name],
                stderr=subprocess.DEVNULL
            ).decode().strip().split('\n')[0].strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            self.ffmpeg_path.replace("ffmpeg", "ffprobe") if "ffmpeg" in self.ffmpeg_path else "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def cut_footage_to_duration(
        self,
        footage_path: str,
        target_duration: float,
        output_path: str = ""
    ) -> str:
        """
        Cut footage to exact target duration using FFmpeg.

        Always re-encodes to ensure frame-accurate cutting.
        Stream copy only cuts at keyframes → causes timing drift.

        - If footage >= target: trim with re-encode
        - If footage < target: loop with FFmpeg stream_loop + trim

        Returns path to output video (video-only, no audio).
        """
        if not output_path:
            stem = Path(footage_path).stem
            output_path = str(self.output_dir / f"{stem}_cut.mp4")

        try:
            footage_duration = self._get_video_duration(footage_path)

            if footage_duration >= target_duration:
                # Trim with re-encode for frame-accurate cut
                cmd = [
                    self.ffmpeg_path, "-y",
                    "-i", footage_path,
                    "-t", str(target_duration),
                    "-an",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-r", "30",
                    output_path,
                ]
            else:
                # Loop + trim: FFmpeg handles looping natively
                loops_needed = int(target_duration / footage_duration) + 1
                cmd = [
                    self.ffmpeg_path, "-y",
                    "-stream_loop", str(loops_needed),
                    "-i", footage_path,
                    "-t", str(target_duration),
                    "-an",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-r", "30",
                    output_path,
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg cut failed: {result.stderr[-300:]}")

            print(f"[VideoAssembler] Cut footage to {target_duration:.1f}s -> {output_path}")
            return output_path

        except Exception as e:
            print(f"[VideoAssembler] Error cutting footage: {e}")
            raise

    def _create_subtitle_clip(
        self,
        text: str,
        duration: float,
        video_width: int,
        video_height: int,
        style: Optional[Dict] = None,
    ):
        """
        Create a TextClip subtitle overlay (VideoGen/Vrew style).

        Positioned at bottom center with semi-transparent background.
        Requires ImageMagick to be installed.
        """
        if not self.has_imagemagick or not text:
            return None

        try:
            from moviepy.editor import TextClip, CompositeVideoClip, ColorClip

            # Defaults (VideoGen-style: white text, dark semi-transparent bg)
            s = style or {}
            fontsize = s.get("fontsize", max(28, int(video_height / 18)))
            font = s.get("font", "Arial-Bold")
            color = s.get("color", "white")
            stroke_color = s.get("stroke_color", "black")
            stroke_width = s.get("stroke_width", 2)
            bg_opacity = s.get("bg_opacity", 0.6)
            margin_bottom = s.get("margin_bottom", int(video_height * 0.08))

            # Create text clip
            txt_clip = TextClip(
                text,
                fontsize=fontsize,
                color=color,
                font=font,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                size=(int(video_width * 0.85), None),
                method='caption',
                align='center',
            ).set_duration(duration)

            # Create semi-transparent background behind text
            txt_w, txt_h = txt_clip.size
            padding = 16
            bg_clip = (
                ColorClip(
                    size=(txt_w + padding * 2, txt_h + padding),
                    color=(0, 0, 0)
                )
                .set_opacity(bg_opacity)
                .set_duration(duration)
            )

            # Position: bottom center
            y_pos = video_height - txt_h - margin_bottom - padding
            bg_clip = bg_clip.set_position(
                ((video_width - txt_w - padding * 2) // 2, y_pos)
            )
            txt_clip = txt_clip.set_position(
                ((video_width - txt_w) // 2, y_pos + padding // 2)
            )

            return [bg_clip, txt_clip]

        except Exception as e:
            print(f"[VideoAssembler] Subtitle creation error: {e}")
            return None

    def assemble_scene(
        self,
        footage_path: str,
        audio_path: str,
        scene_id: int,
        output_path: str = "",
        subtitle_text: str = "",
        subtitle_style: Optional[Dict] = None,
    ) -> str:
        """
        Combine footage + audio for a single scene using FFmpeg.

        Audio duration is the master duration. Footage is cut/looped to match.
        Uses -t audio_duration instead of -shortest to prevent voice cutoff.
        Returns path to assembled scene video.
        """
        if not output_path:
            output_path = str(self.output_dir / f"scene_{scene_id:03d}.mp4")

        try:
            # Get audio duration (this is the MASTER duration)
            audio_duration = self.get_audio_duration(audio_path)

            # Cut footage to audio duration (FFmpeg, re-encode for accuracy)
            cut_footage_path = str(self.output_dir / f"_temp_cut_{scene_id}.mp4")
            self.cut_footage_to_duration(footage_path, audio_duration, cut_footage_path)

            # Mux video + audio — use -t to guarantee full audio length
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", cut_footage_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-t", str(audio_duration),
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg mux failed: {result.stderr[-300:]}")

            # Cleanup temp cut file
            try:
                os.remove(cut_footage_path)
            except OSError:
                pass

            file_size = Path(output_path).stat().st_size
            print(f"[VideoAssembler] Scene {scene_id}: {audio_duration:.1f}s -> {output_path} ({file_size / 1024 / 1024:.1f} MB)")
            return output_path

        except Exception as e:
            print(f"[VideoAssembler] Error assembling scene {scene_id}: {e}")
            raise

    def assemble_subscenes(
        self,
        footage_paths: List[str],
        clip_durations: List[float],
        audio_path: str,
        scene_id: int,
        output_path: str = "",
    ) -> str:
        """
        Assemble a scene from multiple footage clips (sub-scenes).

        Each footage is cut to its clip_duration, then all are concatenated,
        and the full audio is overlaid on the result.

        Args:
            footage_paths: List of downloaded footage file paths
            clip_durations: Duration for each sub-clip (should sum to audio_duration)
            audio_path: Path to the voice audio file
            scene_id: Scene identifier
            output_path: Optional output path

        Returns path to assembled scene video.
        """
        if not output_path:
            output_path = str(self.output_dir / f"scene_{scene_id:03d}.mp4")

        try:
            # Step 1: Cut each footage to its sub-clip duration
            sub_clip_paths = []
            for i, (fp, dur) in enumerate(zip(footage_paths, clip_durations)):
                sub_path = str(self.output_dir / f"_temp_sub_{scene_id}_{i}.mp4")
                self.cut_footage_to_duration(fp, dur, sub_path)
                sub_clip_paths.append(sub_path)

            # Step 2: Concat all sub-clips into one video
            if len(sub_clip_paths) == 1:
                concat_path = sub_clip_paths[0]
            else:
                concat_path = str(self.output_dir / f"_temp_concat_{scene_id}.mp4")
                self._ffmpeg_concat(sub_clip_paths, concat_path, "720p")

            # Step 3: Mux concatenated video + audio — use -t for exact duration
            audio_duration = self.get_audio_duration(audio_path)
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", concat_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-t", str(audio_duration),
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg mux failed: {result.stderr[-300:]}")

            # Cleanup temp files
            for p in sub_clip_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass
            if len(sub_clip_paths) > 1:
                try:
                    os.remove(concat_path)
                except OSError:
                    pass

            audio_duration = self.get_audio_duration(audio_path)
            file_size = Path(output_path).stat().st_size
            print(f"[VideoAssembler] Scene {scene_id}: {len(footage_paths)} sub-clips -> {audio_duration:.1f}s -> {output_path} ({file_size / 1024 / 1024:.1f} MB)")
            return output_path

        except Exception as e:
            print(f"[VideoAssembler] Error assembling scene {scene_id} with sub-scenes: {e}")
            raise

    def _ffmpeg_concat(
        self,
        video_paths: List[str],
        output_path: str,
        video_quality: str = "720p",
    ) -> str:
        """
        Concatenate videos using ffmpeg concat demuxer.

        Always re-encodes with fixed frame rate to prevent
        speed/freeze issues from mixed-source footage.
        """
        quality = QUALITY_PRESETS.get(video_quality, QUALITY_PRESETS["720p"])
        concat_list_path = str(self.output_dir / "_concat_list.txt")

        try:
            # Write concat list file
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for vpath in video_paths:
                    abs_path = str(Path(vpath).resolve())
                    safe_path = abs_path.replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            print(f"[VideoAssembler] ffmpeg concat: {len(video_paths)} videos -> {output_path}")

            # Always re-encode with consistent frame rate (30fps CFR)
            # to prevent speed/freeze issues from mixed-source footage
            cmd = [
                self.ffmpeg_path, "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list_path,
                "-c:v", "libx264",
                "-preset", quality["preset"],
                "-b:v", quality["bitrate"],
                "-vf", f"scale=-2:{quality['height']}",
                "-r", "30",
                "-vsync", "cfr",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg concat failed: {result.stderr[-500:]}"
                )

            return output_path

        finally:
            # Clean up concat list
            try:
                os.remove(concat_list_path)
            except OSError:
                pass

    def assemble_all_scenes(
        self,
        scene_videos: List[Dict],
        output_filename: str = "final_video.mp4",
        transition_duration: float = 0.5,
        bgm_path: str = "",
        bgm_volume: float = 0.15,
        video_quality: str = "720p",
    ) -> str:
        """
        Concatenate all scene videos into a single final video.

        Uses ffmpeg concat demuxer for memory-efficient concatenation.
        Falls back from MoviePy crossfade to ffmpeg on MemoryError.

        Args:
            scene_videos: List of { scene_id, video_path } sorted by scene_id
            output_filename: Name of the final output file
            transition_duration: Crossfade duration in seconds (0 = no transition)
            bgm_path: Path to background music file (empty = no BGM)
            bgm_volume: BGM volume relative to voice (0.0-1.0, default 0.15)
            video_quality: Output quality preset ("480p", "720p", "1080p")

        Returns:
            Path to final assembled video.
        """
        output_path = str(self.output_dir / output_filename)

        try:
            # Sort by scene_id
            sorted_scenes = sorted(scene_videos, key=lambda s: s.get("scene_id", 0))

            # Collect valid video paths
            valid_paths = []
            for scene in sorted_scenes:
                video_path = scene.get("video_path", "")
                if video_path and os.path.exists(video_path):
                    valid_paths.append(video_path)
                    print(f"[VideoAssembler] Queued scene {scene.get('scene_id')}: {video_path}")

            if not valid_paths:
                raise ValueError("No valid scene videos to concatenate")

            # ── Primary: Use ffmpeg concat (memory-safe, no numpy arrays) ──
            print(f"[VideoAssembler] Using ffmpeg concat for {len(valid_paths)} scenes (memory-safe)")
            self._ffmpeg_concat(valid_paths, output_path, video_quality)

            # Force gc to free any lingering memory
            gc.collect()

            file_size = Path(output_path).stat().st_size
            print(f"[VideoAssembler] Final video: {file_size / 1024 / 1024:.1f} MB | {video_quality} -> {output_path}")

            return output_path

        except Exception as e:
            print(f"[VideoAssembler] Error assembling final video: {e}")
            raise

    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of an audio file in seconds."""
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(audio_path)
            if audio and audio.info:
                return audio.info.length
        except Exception:
            pass

        # Fallback: use moviepy
        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(audio_path)
            duration = clip.duration
            clip.close()
            return duration
        except Exception as e:
            print(f"[VideoAssembler] Error getting audio duration: {e}")
            return 0.0

    def cleanup_temp_files(self):
        """Remove temporary cut files."""
        for f in self.output_dir.glob("_temp_cut_*"):
            try:
                os.remove(f)
            except OSError:
                pass
