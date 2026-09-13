"""Google Drive integration for Rehab RCH Agent v2.

Creates and maintains this folder structure::

    Rehab RCH Agent
    ├── Reports
    │   ├── Weekly
    │   ├── Monthly
    │   └── Annual
    ├── Announcements
    ├── SOP
    ├── Meeting Minutes
    └── Knowledge Base

Reports are saved under year/month subfolders, e.g.::

    /Rehab RCH Reports/2026/September/Weekly Summary - 13 Sep 2026.docx

Without ``credentials.json`` the client runs in demo mode: files stay in
local ``output/`` and a descriptive message is returned instead of a
Drive link.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings

log = logging.getLogger(__name__)

FOLDER_MIME = "application/vnd.google-apps.folder"

# (drive path parts, friendly key)
REQUIRED_FOLDERS: list[list[str]] = [
    ["Reports", "Weekly"],
    ["Reports", "Monthly"],
    ["Reports", "Annual"],
    ["Announcements"],
    ["SOP"],
    ["Meeting Minutes"],
    ["Knowledge Base"],
]

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class DriveClient:
    """Service-account Drive client with demo-mode fallback."""

    def __init__(self) -> None:
        self._service = None
        self._root_id: Optional[str] = settings.drive_root_folder_id or None
        self.demo_mode = True
        if not settings.has_google_credentials:
            log.warning("credentials.json not found — Drive running in demo mode.")
            return
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            scopes = [
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(
                str(settings.credentials_path), scopes=scopes
            )
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
            self.demo_mode = False
            log.info("Google Drive client initialised.")
        except Exception as exc:
            log.warning("Drive init failed (%s); demo mode.", exc)
            self._service = None
            self.demo_mode = True

    # -- folders ----------------------------------------------------------
    def ensure_folder_structure(self) -> dict[str, str]:
        """Create root + required subfolders. Returns {path: folder_id}.

        In demo mode returns local output paths instead.
        """
        if self.demo_mode or self._service is None:
            mapping: dict[str, str] = {}
            for parts in REQUIRED_FOLDERS:
                p = settings.output_dir.joinpath(*parts)
                p.mkdir(parents=True, exist_ok=True)
                mapping["/".join(parts)] = str(p)
            return mapping

        root_id = self._ensure_root()
        mapping = {}
        for parts in REQUIRED_FOLDERS:
            folder_id = root_id
            for part in parts:
                folder_id = self._find_or_create_folder(part, folder_id)
            mapping["/".join(parts)] = folder_id
        return mapping

    def dated_reports_path(self, category: str, when: Optional[datetime] = None) -> list[str]:
        """E.g. ['Reports','Weekly','2026','September'] for dated archiving."""
        when = when or datetime.now()
        return ["Reports", category, when.strftime("%Y"), MONTH_NAMES[when.month - 1]]

    # -- upload ------------------------------------------------------------
    def upload_file(
        self,
        local_path: Path | str,
        folder_key: str = "Reports/Weekly",
        dated_subfolders: bool = True,
        mimetype: str = "",
    ) -> dict:
        """Upload a local file to Drive.

        Returns dict with keys: ok, demo, drive_link, folder, filename.
        `mimetype` defaults to .docx, or text/markdown for .md files.
        """
        local_path = Path(local_path)
        filename = local_path.name
        if self.demo_mode or self._service is None:
            return {
                "ok": True,
                "demo": True,
                "drive_link": "",
                "folder": f"local output/{folder_key}",
                "filename": filename,
                "message": (
                    f"✅ Saved locally to `output/{folder_key}/{filename}` "
                    "(demo mode — add credentials.json + share the Drive folder "
                    "with the service account to enable Drive upload)."
                ),
            }
        try:
            from googleapiclient.http import MediaFileUpload

            folder_id = self._ensure_path(folder_key.split("/"), dated_subfolders, filename)
            if not mimetype:
                mimetype = ("text/markdown" if local_path.suffix.lower() == ".md"
                            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            media = MediaFileUpload(str(local_path), mimetype=mimetype, resumable=True)
            created = (
                self._service.files()
                .create(body={"name": filename, "parents": [folder_id]}, media_body=media, fields="id, webViewLink")
                .execute()
            )
            link = created.get("webViewLink", "")
            return {
                "ok": True,
                "demo": False,
                "drive_link": link,
                "folder": folder_key,
                "filename": filename,
                "message": f"✅ Saved to Google Drive: `{folder_key}/{filename}`",
            }
        except Exception as exc:
            log.exception("Drive upload failed: %s", exc)
            return {
                "ok": False,
                "demo": False,
                "drive_link": "",
                "folder": folder_key,
                "filename": filename,
                "message": f"⚠️ Drive upload failed ({exc}). File kept locally at `{local_path}`.",
            }

    def list_files(self, folder_key: str = "Reports/Weekly", limit: int = 10) -> list[dict]:
        if self.demo_mode or self._service is None:
            folder = settings.output_dir.joinpath(*folder_key.split("/"))
            if not folder.exists():
                return []
            return [{"name": p.name} for p in sorted(folder.glob("*")) if p.is_file()][:limit]
        try:
            folder_id = self._resolve_path(folder_key.split("/"))
            if not folder_id:
                return []
            res = (
                self._service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id, name, webViewLink, modifiedTime)",
                    orderBy="modifiedTime desc",
                    pageSize=limit,
                )
                .execute()
            )
            return res.get("files", [])
        except Exception as exc:
            log.warning("Drive list failed: %s", exc)
            return []

    # -- internals ----------------------------------------------------------
    def _ensure_root(self) -> str:
        if self._root_id:
            return self._root_id
        assert self._service is not None
        # Search for existing root folder by name
        res = (
            self._service.files()
            .list(
                q=f"name='{settings.drive_root_folder_name}' and mimeType='{FOLDER_MIME}' and trashed=false",
                fields="files(id, name)",
            )
            .execute()
        )
        files = res.get("files", [])
        if files:
            self._root_id = files[0]["id"]
            return self._root_id
        created = (
            self._service.files()
            .create(body={"name": settings.drive_root_folder_name, "mimeType": FOLDER_MIME}, fields="id")
            .execute()
        )
        self._root_id = created["id"]
        return self._root_id

    def _find_or_create_folder(self, name: str, parent_id: str) -> str:
        assert self._service is not None
        res = (
            self._service.files()
            .list(
                q=f"name='{name}' and '{parent_id}' in parents and mimeType='{FOLDER_MIME}' and trashed=false",
                fields="files(id, name)",
            )
            .execute()
        )
        files = res.get("files", [])
        if files:
            return files[0]["id"]
        created = (
            self._service.files()
            .create(
                body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
                fields="id",
            )
            .execute()
        )
        return created["id"]

    def _resolve_path(self, parts: list[str]) -> Optional[str]:
        folder_id = self._ensure_root()
        assert self._service is not None
        for part in parts:
            res = (
                self._service.files()
                .list(
                    q=f"name='{part}' and '{folder_id}' in parents and mimeType='{FOLDER_MIME}' and trashed=false",
                    fields="files(id)",
                )
                .execute()
            )
            files = res.get("files", [])
            if not files:
                return None
            folder_id = files[0]["id"]
        return folder_id

    def _ensure_path(self, parts: list[str], dated: bool, filename: str) -> str:
        """Ensure folder path exists; append YYYY/Month for Reports."""
        if dated and parts and parts[0] == "Reports" and len(parts) >= 2:
            when = datetime.now()
            parts = parts + [when.strftime("%Y"), MONTH_NAMES[when.month - 1]]
        folder_id = self._ensure_root()
        for part in parts:
            folder_id = self._find_or_create_folder(part, folder_id)
        return folder_id


# Singleton
drive = DriveClient()
