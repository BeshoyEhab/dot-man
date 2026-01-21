"""Backup management for dot-man."""

import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Iterator

from .constants import DOT_MAN_DIR
from .exceptions import BackupError

BACKUPS_DIR = DOT_MAN_DIR / "backups"
MAX_BACKUPS = 5


class BackupManager:
    """Manages local safety snapshots."""

    def __init__(self, backups_dir: Path | None = None):
        self.backups_dir = backups_dir or BACKUPS_DIR
        # Ensure backups directory exists
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def _get_backup_name(self, note: str = "manual") -> str:
        """Generate a unique backup name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize note
        note_safe = "".join(c if c.isalnum() else "_" for c in note)
        return f"{timestamp}_{note_safe}"

    def create_backup(self, paths: list[Path], note: str = "manual") -> str:
        """
        Create a backup snapshot of the given paths.

        Args:
            paths: List of file/directory paths to backup.
            note: Short description/reason for backup.

        Returns:
            The name (ID) of the created backup.
        """
        if not paths:
            return ""

        backup_id = self._get_backup_name(note)
        backup_path = self.backups_dir / backup_id
        
        try:
            backup_path.mkdir()
            
            # Metadata to store original paths relative to home or absolute
            manifest = {}
            count = 0

            for path in paths:
                if not path.exists():
                    continue

                # Determine destination structure within backup
                # We replicate the structure relative to user's home or root
                # For simplicity, we flattening somewhat or mirroring full path?
                # Mirroring full path is safest to avoid collisions.
                # E.g. /home/user/.bashrc -> backup/home/user/.bashrc
                
                # Strip root anchor to make it relative
                rel_path = path.relative_to(path.anchor) 
                dest = backup_path / rel_path
                
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if path.is_file():
                    shutil.copy2(path, dest)
                elif path.is_dir():
                    shutil.copytree(path, dest)
                
                manifest[str(rel_path)] = str(path)
                count += 1

            if count == 0:
                # No files backed up, remove empty directory
                backup_path.rmdir()
                return ""

            # Save manifest
            (backup_path / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )

            # Rotate old backups
            self._rotate_backups()

            return backup_id

        except OSError as e:
            # Cleanup on failure
            if backup_path.exists():
                shutil.rmtree(backup_path, ignore_errors=True)
            raise BackupError(f"Failed to create backup '{backup_id}': {e}")

    def list_backups(self) -> list[dict]:
        """
        List all available backups.
        
        Returns:
            List of dicts with keys: id, date, note, path
        """
        backups = []
        if not self.backups_dir.exists():
            return []

        for p in self.backups_dir.iterdir():
            if p.is_dir():
                # Parse name: YYYYMMDD_HHMMSS_note
                parts = p.name.split("_", 2)
                if len(parts) >= 2:
                    date_str = f"{parts[0]} {parts[1][:2]}:{parts[1][2:4]}"
                    note = parts[2] if len(parts) > 2 else "auto"
                    backups.append({
                        "id": p.name,
                        "date": date_str,
                        "note": note,
                        "path": p
                    })
        
        # Sort by ID (timestamp) descending
        return sorted(backups, key=lambda x: x["id"], reverse=True)

    def restore_backup(self, backup_id: str) -> bool:
        """
        Restore files from a backup.
        
        Args:
           backup_id: The ID (folder name) of the backup to restore.
        """
        backup_path = self.backups_dir / backup_id
        if not backup_path.exists():
            raise BackupError(f"Backup '{backup_id}' not found")

        manifest_file = backup_path / "manifest.json"
        if not manifest_file.exists():
             raise BackupError(f"Backup '{backup_id}' is corrupt (missing manifest)")

        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            
            for rel_path_str, original_path_str in manifest.items():
                start_source = backup_path / rel_path_str
                original_path = Path(original_path_str)
                
                if start_source.exists():
                    # Ensure parent exists
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if original_path.exists():
                        if original_path.is_dir():
                            shutil.rmtree(original_path)
                        else:
                            original_path.unlink()
                    
                    if start_source.is_dir():
                        shutil.copytree(start_source, original_path)
                    else:
                        shutil.copy2(start_source, original_path)
                        
            return True

        except (OSError, json.JSONDecodeError) as e:
             raise BackupError(f"Failed to restore backup '{backup_id}': {e}")

    def _rotate_backups(self) -> None:
        """Keep only the last MAX_BACKUPS backups."""
        backups = self.list_backups()
        if len(backups) > MAX_BACKUPS:
            to_delete = backups[MAX_BACKUPS:]
            for b in to_delete:
                shutil.rmtree(b["path"], ignore_errors=True)
