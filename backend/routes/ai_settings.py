"""
API routes for AI settings management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from modules.ai_settings_db import get_settings_db

router = APIRouter()


class UpdateSettingRequest(BaseModel):
    """Request model for updating a setting"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    gpm_token: Optional[str] = None
    gpm_profile_id: Optional[str] = None


class SetDefaultProviderRequest(BaseModel):
    """Request model for setting default provider"""
    provider: str


@router.get("/settings")
async def get_all_settings():
    """Get all AI settings"""
    try:
        db = get_settings_db()
        settings = db.get_all_settings()
        default_provider = db.get_default_provider()
        active_provider = db.get_active_provider()
        
        return {
            "success": True,
            "settings": settings,
            "default_provider": default_provider,
            "active_provider": active_provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{provider}")
async def get_setting(provider: str):
    """Get settings for a specific provider"""
    try:
        db = get_settings_db()
        setting = db.get_setting(provider)
        
        if not setting:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
        
        return {
            "success": True,
            "setting": setting
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/{provider}")
async def update_setting(provider: str, data: UpdateSettingRequest):
    """Update settings for a specific provider"""
    try:
        db = get_settings_db()
        
        # Validate provider
        valid_providers = ['openai_api', 'gemini_api', 'custom_api']
        if provider not in valid_providers:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Update setting
        success = db.update_setting(
            provider=provider,
            api_key=data.api_key,
            base_url=data.base_url,
            model=data.model,
            gpm_token=data.gpm_token,
            gpm_profile_id=data.gpm_profile_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update setting")
        
        # Get updated setting
        updated_setting = db.get_setting(provider)
        
        return {
            "success": True,
            "message": f"Settings for '{provider}' updated successfully",
            "setting": updated_setting
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/{provider}/test-result")
async def update_test_result(provider: str, test_status: str, test_message: str = ""):
    """Update test result for a provider"""
    try:
        db = get_settings_db()
        
        success = db.update_setting(
            provider=provider,
            test_status=test_status,
            test_message=test_message
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update test result")
        
        return {
            "success": True,
            "message": "Test result updated"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/default-provider")
async def set_default_provider(data: SetDefaultProviderRequest):
    """Set default AI provider"""
    try:
        db = get_settings_db()
        
        # Validate provider
        valid_providers = ['auto', 'openai', 'gemini_api']
        if data.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        success = db.set_default_provider(data.provider)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set default provider")
        
        return {
            "success": True,
            "message": f"Default provider set to '{data.provider}'",
            "provider": data.provider
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/default-provider")
async def get_default_provider():
    """Get default AI provider"""
    try:
        db = get_settings_db()
        provider = db.get_default_provider()
        
        return {
            "success": True,
            "provider": provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SetActiveProviderRequest(BaseModel):
    """Request model for setting active provider"""
    provider: str


@router.post("/settings/active-provider")
async def set_active_provider(data: SetActiveProviderRequest):
    """Set active content AI provider"""
    try:
        db = get_settings_db()
        valid_providers = ['openai', 'gemini_api', 'custom', '']
        if data.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        success = db.set_active_provider(data.provider)
        
        return {
            "success": success,
            "message": f"Active provider set to '{data.provider}'",
            "provider": data.provider
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/active-provider")
async def get_active_provider():
    """Get active content AI provider"""
    try:
        db = get_settings_db()
        provider = db.get_active_provider()
        return {
            "success": True,
            "provider": provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

