"""
Export API Routes — Package queue results into user-selected output directory.

Endpoints:
- POST /package  — Package all selected results into a timestamped subfolder
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import csv
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from modules.tts_engine import VOICE_OUTPUT_DIR
from modules.production_store import get_production_store
from modules.seo_optimizer import SEOOptimizer, SEOData

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════════

class ExportOptions(BaseModel):
    full_script: bool = True
    split_csv: bool = True
    final_video: bool = True
    voice_zip: bool = True
    footage_zip: bool = True
    keywords_txt: bool = True
    prompts_txt: bool = True
    seo_optimize: bool = False  # SEO Thô: rename + inject metadata


class SceneExportData(BaseModel):
    scene_id: int
    content: str = ""
    keywords: List[str] = []
    image_prompt: str = ""
    video_prompt: str = ""


class PackageRequest(BaseModel):
    output_dir: str
    item_id: str = ""
    folder_name: str = ""
    export_options: ExportOptions
    full_script: str = ""
    scenes: List[SceneExportData] = []
    voice_filenames: List[str] = []
    final_video_path: str = ""
    scene_video_paths: List[str] = []
    # Production metadata
    project_name: str = ""
    original_link: str = ""
    description: str = ""
    thumbnail: str = ""
    keywords: str = ""
    upload_platform: str = ""
    channel_name: str = ""
    preset_name: str = ""
    voice_id: str = ""
    settings_snapshot: Dict = {}
    # SEO Thô fields
    seo_data: Optional[Dict] = None  # SEOData dict from /api/seo/generate


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/package")
async def package_results(request: PackageRequest):
    """
    Package queue results into a timestamped subfolder in the user-selected output directory.
    
    Creates: output_dir/Queue_YYYYMMDD_HHmmss/
    Inside:  script_full.txt, scenes.csv, final_video.mp4, voices.zip, footage.zip
    """
    if not request.output_dir:
        raise HTTPException(status_code=400, detail="output_dir is required")

    # Validate output directory exists
    output_base = Path(request.output_dir)
    if not output_base.exists():
        try:
            output_base.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot create output directory: {e}")

    # Create timestamped subfolder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = request.folder_name or f"Queue_{timestamp}"
    export_dir = output_base / folder_name
    export_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "success": True,
        "export_dir": str(export_dir),
        "exported": [],
        "errors": [],
    }

    opts = request.export_options

    # ── 1. Full Script (.txt) ──
    if opts.full_script and request.full_script:
        try:
            script_path = export_dir / "script_full.txt"
            script_path.write_text(request.full_script, encoding="utf-8")
            results["exported"].append("script_full.txt")
            print(f"[Export] Saved full script → {script_path}")
        except Exception as e:
            results["errors"].append(f"script_full.txt: {e}")

    # ── 2. Split Script (.csv) ──
    if opts.split_csv and request.scenes:
        try:
            csv_path = export_dir / "scenes.csv"
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["scene_id", "content", "image_prompt", "video_prompt"])
                for scene in sorted(request.scenes, key=lambda s: s.scene_id):
                    writer.writerow([
                        scene.scene_id,
                        scene.content,
                        scene.image_prompt,
                        scene.video_prompt,
                    ])
            results["exported"].append("scenes.csv")
            print(f"[Export] Saved scenes CSV → {csv_path}")
        except Exception as e:
            results["errors"].append(f"scenes.csv: {e}")

    # ── 2b. Keywords (.txt) ──
    if opts.keywords_txt and request.scenes:
        try:
            kw_lines = []
            for scene in sorted(request.scenes, key=lambda s: s.scene_id):
                kws = scene.keywords if scene.keywords else []
                if kws:
                    kw_lines.append(f"Scene {scene.scene_id}: {', '.join(kws)}")
            if kw_lines:
                kw_path = export_dir / "keywords.txt"
                kw_path.write_text('\n'.join(kw_lines), encoding="utf-8")
                results["exported"].append("keywords.txt")
                print(f"[Export] Saved keywords → {kw_path}")
        except Exception as e:
            results["errors"].append(f"keywords.txt: {e}")

    # ── 2c. Prompts (.txt) ──
    if opts.prompts_txt and request.scenes:
        try:
            prompt_lines = []
            for scene in sorted(request.scenes, key=lambda s: s.scene_id):
                has_any = scene.image_prompt or scene.video_prompt
                if has_any:
                    prompt_lines.append(f"=== Scene {scene.scene_id} ===")
                    if scene.video_prompt:
                        prompt_lines.append(f"[Video Prompt]\n{scene.video_prompt}")
                    if scene.image_prompt:
                        prompt_lines.append(f"[Image Prompt]\n{scene.image_prompt}")
                    prompt_lines.append("")
            if prompt_lines:
                prompts_path = export_dir / "prompts.txt"
                prompts_path.write_text('\n'.join(prompt_lines), encoding="utf-8")
                results["exported"].append("prompts.txt")
                print(f"[Export] Saved prompts → {prompts_path}")
        except Exception as e:
            results["errors"].append(f"prompts.txt: {e}")

    # ── 3. Final Video (.mp4) ──
    if opts.final_video and request.final_video_path:
        try:
            src = Path(request.final_video_path)
            if src.exists():
                dst = export_dir / f"final_video{src.suffix}"
                shutil.copy2(str(src), str(dst))
                results["exported"].append(dst.name)
                print(f"[Export] Copied final video → {dst}")
            else:
                results["errors"].append(f"final_video: source not found ({src})")
        except Exception as e:
            results["errors"].append(f"final_video: {e}")

    # ── 3b. SEO Thô Processing ──
    if opts.seo_optimize and results.get("exported") and request.seo_data:
        try:
            seo = SEOOptimizer()
            seo_data = SEOData.from_dict(request.seo_data)

            # Safety: skip SEO if critical fields are empty (prevents wiping metadata)
            if not seo_data.main_keyword and not seo_data.seo_title:
                results["errors"].append("seo: skipped — empty SEO data (no keyword/title)")
                print("[Export] SEO skipped: empty seo_data (main_keyword and seo_title both empty)")
            else:
                # Find the exported video file
                video_file = None
                for f in export_dir.iterdir():
                    if f.suffix.lower() in (".mp4", ".mkv", ".webm"):
                        video_file = f
                        break

                if video_file:
                    # Generate SEO filename
                    seo_filename = seo.get_seo_filename(seo_data, video_file.suffix)
                    seo_output = export_dir / f"_seo_temp{video_file.suffix}"

                    # Inject metadata
                    seo.inject_metadata(
                        input_path=str(video_file),
                        output_path=str(seo_output),
                        seo_data=seo_data,
                    )

                    # Replace original with SEO version
                    video_file.unlink()
                    seo_final = export_dir / seo_filename
                    seo_output.rename(seo_final)

                    results["seo_applied"] = True
                    results["seo_filename"] = seo_filename
                    results["exported"].append(f"SEO: {seo_filename}")
                    print(f"[Export] SEO Thô applied → {seo_final}")
                else:
                    results["errors"].append("seo: no video file found to optimize")
        except Exception as e:
            results["errors"].append(f"seo: {e}")
            print(f"[Export] SEO processing error: {e}")

    # ── 4. Voice Files (.zip) ──
    if opts.voice_zip and request.voice_filenames:
        try:
            zip_path = export_dir / "voices.zip"
            added = 0
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for filename in request.voice_filenames:
                    filepath = os.path.join(VOICE_OUTPUT_DIR, filename)
                    if os.path.exists(filepath):
                        zf.write(filepath, filename)
                        added += 1
                    else:
                        print(f"[Export] Voice file not found: {filepath}")

            if added > 0:
                results["exported"].append(f"voices.zip ({added} files)")
                print(f"[Export] Zipped {added} voice files → {zip_path}")
            else:
                # Remove empty zip
                zip_path.unlink(missing_ok=True)
                results["errors"].append("voices.zip: no voice files found")
        except Exception as e:
            results["errors"].append(f"voices.zip: {e}")

    # ── 5. Footage Videos (.zip) ──
    if opts.footage_zip and request.scene_video_paths:
        try:
            zip_path = export_dir / "footage.zip"
            added = 0
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for vpath in request.scene_video_paths:
                    src = Path(vpath)
                    if src.exists():
                        zf.write(str(src), src.name)
                        added += 1
                    else:
                        print(f"[Export] Scene video not found: {vpath}")

            if added > 0:
                results["exported"].append(f"footage.zip ({added} files)")
                print(f"[Export] Zipped {added} scene videos → {zip_path}")
            else:
                zip_path.unlink(missing_ok=True)
                results["errors"].append("footage.zip: no scene video files found")
        except Exception as e:
            results["errors"].append(f"footage.zip: {e}")

    results["total_exported"] = len(results["exported"])
    results["total_errors"] = len(results["errors"])

    # NOTE: Production record is created by the frontend (ScriptWorkflow.tsx)
    # via productionApi.create() with full plaintext content.
    # We do NOT create one here to avoid duplicates with stale file paths.

    return results
