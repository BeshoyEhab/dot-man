"""Audit, status, and orphan management mixin for DotManOperations."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Iterator, Optional
import os
import logging

from .secrets import SecretScanner, SecretMatch
from .constants import REPO_DIR

logger = logging.getLogger(__name__)


class StatusMixin:
    """Mixin providing audit, status, and orphan management operations."""

    def audit(self) -> list[tuple[str, list[SecretMatch]]]:
        """
        Scan all sections for secrets.
        
        Returns:
            List of (section_name, matches) tuples
        """
        scanner = SecretScanner()
        results: list[tuple[str, list[SecretMatch]]] = []
        
        for section_name in self.get_sections():
            section = self.get_section(section_name)
            section_matches: list[SecretMatch] = []
            
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                
                if repo_path.is_file() and repo_path.exists():
                    matches = list(scanner.scan_file(repo_path))
                    section_matches.extend(matches)
                elif repo_path.is_dir() and repo_path.exists():
                    matches = list(scanner.scan_directory(repo_path))
                    section_matches.extend(matches)
            
            if section_matches:
                results.append((section_name, section_matches))
        
        return results

    def pre_push_audit(self) -> bool:
        """
        Check for secrets before pushing.
        Returns True if safe to push, False if secrets found.
        """
        audit_results = self.audit()

        strict_mode = self.global_config.strict_mode

        if not audit_results:
            return True

        logger.warning("Pre-push Audit: Secrets detected!")
        for section, matches in audit_results:
            logger.warning("  [%s]: %d secrets", section, len(matches))

        if strict_mode:
            logger.warning("Strict mode enabled. Push aborted.")
            return False

        from .ui import confirm
        return confirm("Secrets detected. Push anyway?", default=False)

    def get_detailed_status(self) -> Iterator[dict]:
        """
        Get detailed status for all tracked files.

        Yields:
            Dict with: section, local_path, repo_path, status, inherits
        """
        for section_name in self.get_sections():
            section = self.get_section(section_name)

            for local_path, repo_path, status in self.iter_section_paths(section):
                yield {
                    "section": section_name,
                    "local_path": local_path,
                    "repo_path": repo_path,
                    "status": status,
                    "inherits": section.inherits,
                }

    def get_status_summary(self) -> dict:
        """
        Get a summary of current status.
        
        Returns dict with:
            - branch: current branch name
            - sections: number of sections
            - total_paths: total paths tracked
            - modified: number of modified files
            - new: number of new files
            - deleted: number of deleted files
        """
        summary: dict[str, Any] = {
            "branch": self.current_branch,
            "sections": 0,
            "total_paths": 0,
            "modified": 0,
            "new": 0,
            "deleted": 0,
            "identical": 0,
        }
        
        section_names = set()
        
        for item in self.get_detailed_status():
            section_names.add(item["section"])
            summary["total_paths"] += 1
            
            status = item["status"]
            if status == "MODIFIED":
                summary["modified"] += 1
            elif status == "NEW":
                summary["new"] += 1
            elif status == "DELETED":
                summary["deleted"] += 1
            else:
                summary["identical"] += 1
        
        summary["sections"] = len(section_names)
        return summary

    def get_orphaned_files(self) -> list[Path]:
        """
        Identify files in the repository that are not tracked by any section.
        
        Returns:
            List of absolute paths to orphaned files.
        """
        repo_files: set[Path] = set()
        internal_files = {".gitignore", "dot-man.toml", "dot-man.ini"}
        
        for root, dirs, files in os.walk(REPO_DIR):
            root_path = Path(root)
            
            if ".git" in dirs:
                dirs.remove(".git")
                
            for file in files:
                if file in internal_files and root_path == REPO_DIR:
                    continue
                    
                path = root_path / file
                repo_files.add(path)

        tracked_files: set[Path] = set()
        
        for section_name in self.get_sections():
            section = self.get_section(section_name)
            
            if section.repo_path:
                full_repo_path = REPO_DIR / section.repo_path
                if full_repo_path.exists():
                    tracked_files.add(full_repo_path)
            
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                
                if repo_path.exists():
                    if repo_path.is_file():
                        tracked_files.add(repo_path)
                    elif repo_path.is_dir():
                        for p in repo_path.rglob("*"):
                            if p.is_file():
                                tracked_files.add(p)
                                
        orphans = list(repo_files - tracked_files)
        return sorted(orphans)

    def clean_orphaned_files(self, dry_run: bool = False) -> list[Path]:
        """
        Delete orphaned files from the repository.
        
        Args:
            dry_run: If True, only return list of files that would be deleted.
            
        Returns:
            List of deleted (or to be deleted) files.
        """
        orphans = self.get_orphaned_files()
        
        if not dry_run:
            deleted = []
            for orphan in orphans:
                try:
                    if orphan.exists():
                        orphan.unlink()
                        deleted.append(orphan)
                        
                        parent = orphan.parent
                        while parent != REPO_DIR and parent != REPO_DIR.parent:
                            try:
                                parent.rmdir()
                                parent = parent.parent
                            except OSError:
                                break
                                
                except OSError as e:
                    logger.warning("Failed to delete %s: %s", orphan, e)
            return deleted
            
        return orphans
