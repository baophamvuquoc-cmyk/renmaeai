"""
SEO API Routes — Generate and apply SEO Thô optimization to video files.

Endpoints:
- POST /generate      — AI-generate SEO data from script content
- POST /apply         — Apply SEO metadata + rename to a video file
- POST /read-metadata — Read current metadata from a video file
- POST /create-variant — Create hash-unique variant of a video
- POST /batch         — Apply SEO to multiple videos at once
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import asyncio

from modules.seo_optimizer import SEOOptimizer, SEOData
from modules.ai_automation import HybridAIClient

router = APIRouter()
_seo = SEOOptimizer()


# ═══════════════════════════════════════════════════════════════════════════════
# Request / Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateSEORequest(BaseModel):
    script_content: str
    language: str = "vi"
    channel_name: str = ""
    target_platform: str = "youtube"


class SEODataModel(BaseModel):
    main_keyword: str = ""
    secondary_keywords: List[str] = []
    seo_title: str = ""
    seo_description: str = ""
    seo_tags: List[str] = []
    seo_filename: str = ""
    channel_name: str = ""
    target_platform: str = "youtube"


class ApplySEORequest(BaseModel):
    input_path: str
    output_dir: str
    seo_data: SEODataModel
    create_variant: bool = False
    variant_method: str = "metadata"  # metadata | pad | noise | bitrate


class ReadMetadataRequest(BaseModel):
    filepath: str


class CreateVariantRequest(BaseModel):
    input_path: str
    output_path: str
    method: str = "metadata"


class BatchSEORequest(BaseModel):
    items: List[ApplySEORequest]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/generate")
async def generate_seo(request: GenerateSEORequest):
    """
    AI-generate SEO data (keywords, title, description, tags, filename) from script content.

    Mode: Auto — AI generates everything, user can review/edit before applying.
    """
    if not request.script_content.strip():
        raise HTTPException(status_code=400, detail="script_content is required")

    try:
        ai_client = HybridAIClient()
        seo_data = await _seo.generate_seo_data(
            script_content=request.script_content,
            ai_client=ai_client,
            language=request.language,
            channel_name=request.channel_name,
        )
        seo_data.target_platform = request.target_platform

        # Validate: SEO data must have at least main_keyword and seo_title
        if not seo_data.main_keyword or not seo_data.seo_title:
            return {
                "success": False,
                "error": "AI failed to generate valid SEO data (empty keyword/title)",
                "seo_data": seo_data.to_dict(),
            }

        return {
            "success": True,
            "seo_data": seo_data.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEO generation failed: {e}")


@router.post("/apply")
async def apply_seo(request: ApplySEORequest):
    """
    Apply SEO Thô to a video file: rename with SEO slug + inject metadata via FFmpeg.

    Optionally create a hash-unique variant for multi-channel distribution.
    """
    if not request.input_path or not os.path.exists(request.input_path):
        raise HTTPException(status_code=400, detail=f"Input file not found: {request.input_path}")
    if not request.output_dir:
        raise HTTPException(status_code=400, detail="output_dir is required")

    try:
        seo_data = SEOData(
            main_keyword=request.seo_data.main_keyword,
            secondary_keywords=request.seo_data.secondary_keywords,
            seo_title=request.seo_data.seo_title,
            seo_description=request.seo_data.seo_description,
            seo_tags=request.seo_data.seo_tags,
            seo_filename=request.seo_data.seo_filename,
            channel_name=request.seo_data.channel_name,
            target_platform=request.seo_data.target_platform,
        )

        result = _seo.apply_seo_to_video(
            input_path=request.input_path,
            output_dir=request.output_dir,
            seo_data=seo_data,
            create_variant=request.create_variant,
            variant_method=request.variant_method,
        )
        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEO application failed: {e}")


@router.post("/read-metadata")
async def read_metadata(request: ReadMetadataRequest):
    """Read existing metadata from a video file using ffprobe."""
    if not request.filepath or not os.path.exists(request.filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {request.filepath}")

    return _seo.read_metadata(request.filepath)


@router.post("/create-variant")
async def create_variant(request: CreateVariantRequest):
    """
    Create a hash-unique variant of a video for multi-channel distribution.

    Each variant has a different MD5 hash to avoid duplicate content filters.
    """
    if not request.input_path or not os.path.exists(request.input_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.input_path}")

    try:
        result_path = _seo.create_unique_variant(
            input_path=request.input_path,
            output_path=request.output_path,
            method=request.method,
        )

        original_md5 = SEOOptimizer._compute_md5(request.input_path)
        variant_md5 = SEOOptimizer._compute_md5(result_path)

        return {
            "success": True,
            "variant_path": result_path,
            "original_md5": original_md5,
            "variant_md5": variant_md5,
            "hash_changed": original_md5 != variant_md5,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant creation failed: {e}")


@router.post("/batch")
async def batch_seo(request: BatchSEORequest):
    """
    Apply SEO Thô to multiple video files at once.

    Processes each item sequentially to avoid FFmpeg conflicts.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="No items to process")

    results = []
    for i, item in enumerate(request.items):
        try:
            seo_data = SEOData(
                main_keyword=item.seo_data.main_keyword,
                secondary_keywords=item.seo_data.secondary_keywords,
                seo_title=item.seo_data.seo_title,
                seo_description=item.seo_data.seo_description,
                seo_tags=item.seo_data.seo_tags,
                seo_filename=item.seo_data.seo_filename,
                channel_name=item.seo_data.channel_name,
                target_platform=item.seo_data.target_platform,
            )

            result = _seo.apply_seo_to_video(
                input_path=item.input_path,
                output_dir=item.output_dir,
                seo_data=seo_data,
                create_variant=item.create_variant,
                variant_method=item.variant_method,
            )
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e),
                "input_path": item.input_path,
            })

    return {
        "total": len(results),
        "succeeded": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }
