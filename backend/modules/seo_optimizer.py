"""
SEO Thô (Raw SEO) Optimizer — Pre-export SEO processing for video files.

Techniques (from MMO community best practices 2025-2026):
1. AI-powered keyword generation from script content
2. SEO-optimized file naming (slug format)
3. FFmpeg metadata injection (title, tags, description, artist)
4. MD5 hash uniqueness — create distinct file hashes for multi-channel distribution
5. Batch processing for queue items

Usage:
    from modules.seo_optimizer import SEOOptimizer

    seo = SEOOptimizer()
    result = seo.generate_seo_data(script_content, ai_client)
    seo.apply_seo_to_video(input_path, output_path, seo_data)
"""

import os
import re
import uuid
import subprocess
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict

from modules.ffmpeg_setup import get_ffmpeg_path, get_ffprobe_path
from modules.logging_config import get_automation_logger

logger = get_automation_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SEOData:
    """Container for all SEO optimization data."""
    main_keyword: str = ""
    secondary_keywords: List[str] = field(default_factory=list)
    seo_title: str = ""
    seo_description: str = ""
    seo_tags: List[str] = field(default_factory=list)
    seo_filename: str = ""
    channel_name: str = ""
    target_platform: str = "youtube"  # youtube | tiktok | facebook

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "SEOData":
        return SEOData(**{k: v for k, v in data.items() if k in SEOData.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════════════
# SEO Prompt Templates
# ═══════════════════════════════════════════════════════════════════════════════

SEO_GENERATION_PROMPT_VI = """Bạn là chuyên gia SEO video cho YouTube. Dựa trên nội dung script video bên dưới, hãy tạo dữ liệu SEO tối ưu.

**Nội dung video:**
{script_content}

**Ngôn ngữ mục tiêu:** {language}

**YÊU CẦU:** Trả về JSON thuần với cấu trúc chính xác sau (KHÔNG markdown, KHÔNG ```json):
{{
  "main_keyword": "từ khóa chính 4-7 từ, long-tail, ít cạnh tranh",
  "secondary_keywords": ["từ khóa phụ 1", "từ khóa phụ 2", "từ khóa phụ 3"],
  "seo_title": "Tiêu đề SEO tối ưu cho YouTube (60-70 ký tự, chứa từ khóa chính)",
  "seo_description": "Mô tả SEO 200-500 ký tự, chứa từ khóa tự nhiên, có call-to-action",
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "seo_filename": "tu-khoa-chinh-tu-khoa-phu-khong-dau"
}}

**Quy tắc:**
- main_keyword: 4-7 từ, đuôi dài (long-tail), nhắm vào nhu cầu cụ thể
- seo_title: Phải chứa main_keyword, gây tò mò, dưới 70 ký tự
- seo_description: 2-3 câu, chứa main_keyword + 1-2 secondary keywords tự nhiên
- seo_tags: 10-15 tags, mix giữa broad và specific, bao gồm cả biến thể
- seo_filename: Không dấu tiếng Việt, nối bằng gạch ngang, viết thường
- Nếu nội dung tiếng Việt → tags và filename viết không dấu
"""

SEO_GENERATION_PROMPT_EN = """You are a YouTube SEO expert. Based on the video script content below, generate optimized SEO data.

**Video content:**
{script_content}

**Target language:** {language}

**REQUIREMENT:** Return pure JSON with exactly this structure (NO markdown, NO ```json):
{{
  "main_keyword": "main keyword 4-7 words, long-tail, low competition, in {language}",
  "secondary_keywords": ["secondary keyword 1", "secondary keyword 2", "secondary keyword 3"],
  "seo_title": "SEO-optimized YouTube title (60-70 chars, contains main keyword, in {language})",
  "seo_description": "SEO description 200-500 chars, contains keywords naturally, has call-to-action, in {language}",
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "seo_filename": "main-keyword-secondary-keyword-ascii-only"
}}

**Rules:**
- main_keyword: 4-7 words, long-tail, targeting specific needs, written in {language}
- seo_title: Must contain main_keyword, create curiosity, under 70 characters, written in {language}
- seo_description: 2-3 sentences, contains main_keyword + 1-2 secondary keywords naturally, in {language}
- seo_tags: 10-15 tags in {language}, mix broad and specific, include variations
- seo_filename: ASCII only (no accents/diacritics), hyphen-separated, lowercase
"""


def _get_seo_prompt(language: str) -> str:
    """Return the appropriate SEO prompt template based on language."""
    if language == "vi":
        return SEO_GENERATION_PROMPT_VI
    return SEO_GENERATION_PROMPT_EN


# ═══════════════════════════════════════════════════════════════════════════════
# Core SEO Optimizer
# ═══════════════════════════════════════════════════════════════════════════════

class SEOOptimizer:
    """
    SEO Thô processor — optimizes video files before upload.

    Handles:
    - AI keyword generation (auto mode)
    - File naming with SEO slugs
    - FFmpeg metadata injection
    - MD5 hash uniqueness for multi-channel distribution
    """

    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.ffprobe = get_ffprobe_path()

    # ── 1. AI Keyword Generation ──────────────────────────────────────────────

    async def generate_seo_data(
        self,
        script_content: str,
        ai_client,
        language: str = "vi",
        channel_name: str = "",
    ) -> SEOData:
        """
        Use AI to generate SEO keywords, title, description, tags from script.

        Args:
            script_content: Full video script text
            ai_client: HybridAIClient instance
            language: Target language code
            channel_name: Channel name for metadata

        Returns:
            SEOData with all fields populated
        """
        if not script_content.strip():
            logger.warning("[SEO] Empty script content, returning empty SEO data")
            return SEOData()

        # Truncate very long scripts to first 2000 chars for prompt efficiency
        truncated = script_content[:2000] if len(script_content) > 2000 else script_content

        # Use language-appropriate prompt template
        prompt_template = _get_seo_prompt(language)
        lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "es": "Spanish", "fr": "French", "th": "Thai", "de": "German", "pt": "Portuguese", "ru": "Russian"}
        lang_name = lang_names.get(language, "English")
        
        prompt = prompt_template.format(
            script_content=truncated,
            language=lang_name,
        )

        try:
            logger.info(f"[SEO] Generating SEO data via AI (lang={language})...")
            response = await ai_client.generate(prompt, temperature=0.4)

            # Parse JSON from response — handle markdown wrapping
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = re.sub(r"^```(?:json)?\s*", "", json_str)
                json_str = re.sub(r"\s*```$", "", json_str)

            data = json.loads(json_str)
            seo = SEOData(
                main_keyword=data.get("main_keyword", ""),
                secondary_keywords=data.get("secondary_keywords", []),
                seo_title=data.get("seo_title", ""),
                seo_description=data.get("seo_description", ""),
                seo_tags=data.get("seo_tags", []),
                seo_filename=data.get("seo_filename", ""),
                channel_name=channel_name,
            )

            # Sanitize filename
            if seo.seo_filename:
                seo.seo_filename = self._sanitize_filename(seo.seo_filename)

            logger.info(f"[SEO] Generated: title='{seo.seo_title}', tags={len(seo.seo_tags)}")
            return seo

        except json.JSONDecodeError as e:
            logger.error(f"[SEO] Failed to parse AI response as JSON: {e}")
            logger.debug(f"[SEO] Raw response: {response[:500]}")
            # Return partial data from what we can extract
            return SEOData(
                main_keyword=script_content[:50].replace("\n", " "),
                seo_filename=self._text_to_slug(script_content[:60]),
            )
        except Exception as e:
            logger.error(f"[SEO] AI generation failed: {e}")
            return SEOData()

    # ── 2. SEO File Naming ────────────────────────────────────────────────────

    def get_seo_filename(self, seo_data: SEOData, extension: str = ".mp4") -> str:
        """
        Generate SEO-optimized filename.

        Format: main-keyword-secondary.mp4
        """
        if seo_data.seo_filename:
            slug = seo_data.seo_filename
        elif seo_data.main_keyword:
            slug = self._text_to_slug(seo_data.main_keyword)
        else:
            slug = f"video-{uuid.uuid4().hex[:8]}"

        # Ensure extension
        if not extension.startswith("."):
            extension = f".{extension}"

        return f"{slug}{extension}"

    # ── 3. Metadata Injection via FFmpeg ──────────────────────────────────────

    def inject_metadata(
        self,
        input_path: str,
        output_path: str,
        seo_data: SEOData,
    ) -> str:
        """
        Inject SEO metadata into video file using FFmpeg.

        Clears old metadata first, then writes:
        - title: SEO title
        - artist: Channel name
        - comment: Tags (comma-separated)
        - description: SEO description
        - date: Current year

        Args:
            input_path: Source video file
            output_path: Destination video file
            seo_data: SEO data to inject

        Returns:
            Path to output file
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        # Build FFmpeg command
        cmd = [
            self.ffmpeg,
            "-i", input_path,
            "-map_metadata", "-1",  # Clear ALL old metadata
        ]

        # Add metadata fields
        if seo_data.seo_title:
            cmd.extend(["-metadata", f"title={seo_data.seo_title}"])
        if seo_data.channel_name:
            cmd.extend(["-metadata", f"artist={seo_data.channel_name}"])
        if seo_data.seo_tags:
            tags_str = ", ".join(seo_data.seo_tags)
            cmd.extend(["-metadata", f"comment={tags_str}"])
        if seo_data.seo_description:
            cmd.extend(["-metadata", f"description={seo_data.seo_description}"])
        if seo_data.main_keyword:
            cmd.extend(["-metadata", f"keywords={seo_data.main_keyword}"])

        # Add year
        from datetime import datetime
        cmd.extend(["-metadata", f"date={datetime.now().year}"])

        # Stream copy — no re-encoding, just metadata change
        cmd.extend([
            "-c", "copy",
            "-y",  # Overwrite output
            output_path,
        ])

        logger.info(f"[SEO] Injecting metadata: {seo_data.seo_title}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error(f"[SEO] FFmpeg metadata injection failed: {result.stderr[:500]}")
            raise RuntimeError(f"FFmpeg metadata injection failed: {result.stderr[:200]}")

        logger.info(f"[SEO] Metadata injected → {output_path}")
        return output_path

    # ── 4. MD5 Hash Uniqueness ────────────────────────────────────────────────

    def create_unique_variant(
        self,
        input_path: str,
        output_path: str,
        method: str = "metadata",
    ) -> str:
        """
        Create a file-level unique variant of a video to avoid duplicate detection.

        Methods:
        - "metadata": Add unique ID to metadata (fastest, no re-encode)
        - "pad": Add 1px invisible pad (visual change, needs re-encode)
        - "noise": Add subtle noise (minimal visual impact, needs re-encode)
        - "bitrate": Change audio bitrate slightly (fast, minimal quality change)

        Args:
            input_path: Source video
            output_path: Output video
            method: Uniqueness method

        Returns:
            Path to unique variant
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        unique_id = uuid.uuid4().hex

        if method == "metadata":
            # Re-encode audio with random bitrate → guaranteed unique hash
            import random
            random_bitrate = f"{random.randint(125, 135)}k"
            cmd = [
                self.ffmpeg,
                "-i", input_path,
                "-metadata", f"encoder={unique_id}",
                "-metadata", f"unique_id={unique_id}",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", random_bitrate,
                "-y", output_path,
            ]
        elif method == "pad":
            # Add 2px transparent padding (changes visual hash)
            cmd = [
                self.ffmpeg,
                "-i", input_path,
                "-vf", "pad=iw+2:ih:1:0:black",
                "-c:a", "copy",
                "-y", output_path,
            ]
        elif method == "noise":
            # Add very subtle noise (barely visible)
            cmd = [
                self.ffmpeg,
                "-i", input_path,
                "-vf", "noise=alls=2:allf=t",
                "-c:a", "copy",
                "-y", output_path,
            ]
        elif method == "bitrate":
            # Slightly change audio bitrate
            cmd = [
                self.ffmpeg,
                "-i", input_path,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "129k",
                "-y", output_path,
            ]
        else:
            raise ValueError(f"Unknown uniqueness method: {method}")

        logger.info(f"[SEO] Creating unique variant (method={method})")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"[SEO] Variant creation failed: {result.stderr[:500]}")
            raise RuntimeError(f"Variant creation failed: {result.stderr[:200]}")

        logger.info(f"[SEO] Unique variant created → {output_path}")
        return output_path

    # ── 5. Full SEO Pipeline ──────────────────────────────────────────────────

    def apply_seo_to_video(
        self,
        input_path: str,
        output_dir: str,
        seo_data: SEOData,
        create_variant: bool = False,
        variant_method: str = "metadata",
    ) -> Dict:
        """
        Apply full SEO Thô pipeline to a single video file.

        Steps:
        1. Generate SEO filename
        2. Inject metadata via FFmpeg
        3. Optionally create hash-unique variant

        Args:
            input_path: Source video file
            output_dir: Directory for output
            seo_data: SEO data to apply
            create_variant: Whether to create hash-unique variant
            variant_method: Method for hash uniqueness

        Returns:
            Dict with paths and metadata
        """
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Generate SEO filename
        src = Path(input_path)
        seo_filename = self.get_seo_filename(seo_data, src.suffix)
        output_path = os.path.join(output_dir, seo_filename)

        # Step 2: Inject metadata
        self.inject_metadata(input_path, output_path, seo_data)

        # Step 3: Create variant if requested
        variant_path = ""
        if create_variant:
            variant_filename = seo_filename.replace(
                src.suffix, f"-v{uuid.uuid4().hex[:4]}{src.suffix}"
            )
            variant_path = os.path.join(output_dir, variant_filename)
            self.create_unique_variant(output_path, variant_path, variant_method)

        # Compute hashes for verification
        original_md5 = self._compute_md5(input_path)
        output_md5 = self._compute_md5(output_path)
        variant_md5 = self._compute_md5(variant_path) if variant_path else ""

        result = {
            "success": True,
            "original_file": input_path,
            "seo_file": output_path,
            "seo_filename": seo_filename,
            "variant_file": variant_path,
            "original_md5": original_md5,
            "seo_md5": output_md5,
            "variant_md5": variant_md5,
            "hash_changed": original_md5 != output_md5,
            "seo_data": seo_data.to_dict(),
        }

        logger.info(
            f"[SEO] Pipeline complete: {seo_filename} "
            f"(hash changed: {result['hash_changed']})"
        )
        return result

    # ── 6. Read Existing Metadata ─────────────────────────────────────────────

    def read_metadata(self, filepath: str) -> Dict:
        """
        Read existing metadata from a video file using ffprobe.

        Returns:
            Dict with metadata fields
        """
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}

        cmd = [
            self.ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            filepath,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                fmt = data.get("format", {})
                return {
                    "filename": fmt.get("filename", ""),
                    "duration": fmt.get("duration", ""),
                    "size": fmt.get("size", ""),
                    "format": fmt.get("format_name", ""),
                    "tags": fmt.get("tags", {}),
                }
            return {"error": f"ffprobe failed: {result.stderr[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    # ── Utility Methods ───────────────────────────────────────────────────────

    @staticmethod
    def _text_to_slug(text: str) -> str:
        """Convert text to URL-safe slug (universal diacritics removal)."""
        import unicodedata
        
        text = text.lower().strip()
        
        # Special handling for Cyrillic (Russian) — transliterate to Latin
        cyrillic_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        }
        result_chars = []
        for ch in text:
            if ch in cyrillic_map:
                result_chars.append(cyrillic_map[ch])
            else:
                result_chars.append(ch)
        text = ''.join(result_chars)
        
        # Special handling for Vietnamese đ (not decomposed by NFKD)
        text = text.replace('đ', 'd').replace('Đ', 'd')
        # Special handling for German ß
        text = text.replace('ß', 'ss')
        
        # Universal diacritics removal via Unicode decomposition
        # NFKD decomposes characters like é → e + ́ (combining acute accent)
        text = unicodedata.normalize('NFKD', text)
        # Remove combining diacritical marks (category 'Mn')
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        
        # Replace non-alphanumeric with hyphens
        text = re.sub(r"[^a-z0-9]+", "-", text)
        # Remove leading/trailing hyphens and collapse multiples
        text = re.sub(r"-+", "-", text).strip("-")
        # Limit length
        if len(text) > 80:
            text = text[:80].rstrip("-")

        return text

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename — keep only safe chars."""
        filename = re.sub(r"[^a-z0-9\-]", "", filename.lower())
        filename = re.sub(r"-+", "-", filename).strip("-")
        return filename or f"video-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _compute_md5(filepath: str) -> str:
        """Compute MD5 hash of a file."""
        if not filepath or not os.path.exists(filepath):
            return ""
        hasher = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
