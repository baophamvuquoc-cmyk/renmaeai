import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class FileManager:
    """Core file management module with pathlib and regex support"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else None
    
    def list_directory(self, path: str) -> List[Dict]:
        """List all files and directories in the given path"""
        dir_path = Path(path)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")
        
        files = []
        for item in dir_path.iterdir():
            try:
                stat = item.stat()
                files.append({
                    "path": str(item),
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "extension": item.suffix if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except (PermissionError, OSError) as e:
                print(f"Error accessing {item}: {e}")
                continue
        
        # Don't sort here - let frontend handle sorting based on user preferences
        return files
    
    def generate_rename_preview(
        self,
        files: List[str],
        pattern: Dict
    ) -> Dict[str, str]:
        """Generate a preview of renamed files without executing"""
        preview = {}
        
        # Check if using sequential naming mode
        name_list_raw = pattern.get("nameList", "")
        use_sequential = pattern.get("useSequentialMode", False)
        
        if use_sequential and name_list_raw and name_list_raw.strip():
            # Sequential naming mode: use comma-separated name list
            name_list = [name.strip() for name in name_list_raw.split(",") if name.strip()]
            
            for index, filepath in enumerate(files):
                path = Path(filepath)
                extension = path.suffix
                
                # Get the corresponding name from the list
                if index < len(name_list):
                    # Use the name from the list
                    new_name = name_list[index]
                else:
                    # More files than names: append index to last name
                    last_name = name_list[-1] if name_list else "file"
                    overflow_index = index - len(name_list) + 2
                    new_name = f"{last_name}_{overflow_index}"
                
                # Add extension
                new_name += extension
                
                # Create new path
                new_path = path.parent / new_name
                preview[filepath] = str(new_path)
        else:
            # Pattern mode: use existing logic
            for index, filepath in enumerate(files, start=pattern.get("indexStart", 1)):
                path = Path(filepath)
                
                # Get original filename and extension
                original_name = path.stem
                extension = path.suffix
                
                # Apply simple keyword replacement first (if provided and includeOriginalName is True)
                if pattern.get("includeOriginalName", False) and pattern.get("findKeyword") and pattern.get("replaceKeyword") is not None:
                    original_name = original_name.replace(
                        pattern["findKeyword"],
                        pattern["replaceKeyword"]
                    )
                
                # Then apply regex replacement to original name if provided and includeOriginalName is True
                elif pattern.get("includeOriginalName", False) and pattern.get("regex") and pattern.get("replacement") is not None:
                    try:
                        original_name = re.sub(
                            pattern["regex"],
                            pattern["replacement"],
                            original_name
                        )
                    except re.error as e:
                        print(f"Invalid regex pattern: {e}")
                
                # Build new filename based on selected components ONLY
                new_name = ""
                
                # Add prefix ONLY if includePrefix is True
                if pattern.get("includePrefix", True) and pattern.get("prefix"):
                    new_name += pattern["prefix"]
                
                # Add index ONLY if useIndex is True
                if pattern.get("useIndex", True):
                    padding = pattern.get("indexPadding", 3)
                    index_str = str(index).zfill(padding)
                    new_name += index_str
                
                # Add original name ONLY if includeOriginalName is True
                if pattern.get("includeOriginalName", False) and original_name:
                    # Add separator if there's already content
                    if new_name:
                        new_name += "_"
                    new_name += original_name
                
                # Add suffix ONLY if includeSuffix is True
                if pattern.get("includeSuffix", True) and pattern.get("suffix"):
                    new_name += pattern["suffix"]
                
                # Add extension ONLY if includeExtension is True
                if pattern.get("includeExtension", True) and extension:
                    new_name += extension
                
                # Safety check: ensure new_name is not empty
                if not new_name:
                    new_name = "renamed_file"
                
                # Create new path
                new_path = path.parent / new_name
                preview[filepath] = str(new_path)
        
        return preview
    
    def execute_rename(self, rename_map: Dict[str, str]) -> Dict:
        """Execute the rename operation with safety checks"""
        success_count = 0
        errors = []
        
        # Check for conflicts
        new_names = list(rename_map.values())
        if len(new_names) != len(set(new_names)):
            return {
                "success": False,
                "error": "Duplicate filenames detected in rename map",
                "count": 0
            }
        
        # Execute renames
        for old_path, new_path in rename_map.items():
            try:
                old = Path(old_path)
                new = Path(new_path)
                
                # Safety checks
                if not old.exists():
                    errors.append(f"Source file not found: {old_path}")
                    continue
                
                if new.exists():
                    errors.append(f"Target file already exists: {new_path}")
                    continue
                
                # Perform rename
                old.rename(new)
                success_count += 1
                
            except (PermissionError, OSError) as e:
                errors.append(f"Error renaming {old_path}: {str(e)}")
        
        return {
            "success": len(errors) == 0,
            "count": success_count,
            "errors": errors if errors else None
        }
    
    def get_file_metadata(self, filepath: str) -> Dict:
        """Extract detailed metadata from a file"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        stat = path.stat()
        
        return {
            "path": str(path),
            "name": path.name,
            "stem": path.stem,
            "extension": path.suffix,
            "size": stat.st_size,
            "size_human": self._format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
        }
    
    @staticmethod
    def _format_size(bytes: int) -> str:
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} PB"
