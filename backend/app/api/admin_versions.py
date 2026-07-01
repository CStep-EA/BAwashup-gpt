"""
Bower Ag CowCare Tool — Admin Version Log API
Sprint 11: Version/release log management.
Sprint 21: GitHub sync — auto-populate from merged PRs and releases.

GET: admin_manager, org_admin
POST: org_admin ONLY (creating releases is a privileged operation)
POST /sync-github: org_admin — fetches latest PRs/releases from GitHub
EXPORT: admin_manager, org_admin

Auth varies per endpoint — see docstrings.
"""

import csv
import io
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.core.auth import CurrentUser, require_role, ADMIN_ROLES
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/versions", tags=["Admin Versions"])

# GitHub configuration
GITHUB_REPO = os.getenv("GITHUB_REPO", "CStep-EA/BAwashup-gpt")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


# ─── Models ───────────────────────────────────────────────────────────────────

class VersionLogItem(BaseModel):
    id: str
    version_tag: str
    release_date: Optional[str] = None
    release_notes: Optional[str] = None
    breaking_changes: Optional[str] = None
    bugs_resolved: Optional[list[str]] = None
    deployed_by: Optional[str] = None
    created_at: str


class CreateVersionRequest(BaseModel):
    version_tag: str = Field(..., min_length=1)
    release_notes: Optional[str] = None
    breaking_changes: Optional[str] = None
    bugs_resolved: Optional[list[str]] = None

    @field_validator("version_tag")
    @classmethod
    def validate_version_tag(cls, v: str) -> str:
        """Validate version_tag format: vX.Y.Z or vX.Y.Z-beta"""
        pattern = r"^v\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid version tag '{v}'. Expected format: vX.Y.Z or vX.Y.Z-suffix"
            )
        return v


class GitHubSyncResponse(BaseModel):
    synced_releases: int
    synced_prs: int
    new_versions_created: int
    message: str


class ChangelogEntry(BaseModel):
    id: str
    version_tag: str
    release_date: Optional[str] = None
    release_notes: Optional[str] = None
    breaking_changes: Optional[str] = None
    bugs_resolved: Optional[list[str]] = None
    pr_number: Optional[int] = None
    pr_title: Optional[str] = None
    pr_url: Optional[str] = None
    source: Optional[str] = None  # "manual", "github_release", "github_pr"
    created_at: str


# ─── GET /admin/versions ──────────────────────────────────────────────────────

@router.get("", response_model=list[VersionLogItem])
async def list_versions(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """List all version_log rows, newest first."""
    client = get_supabase_client()

    try:
        result = (
            client.table("version_log")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    return [
        VersionLogItem(
            id=r["id"],
            version_tag=r["version_tag"],
            release_date=str(r.get("release_date", "")) if r.get("release_date") else None,
            release_notes=r.get("release_notes"),
            breaking_changes=r.get("breaking_changes"),
            bugs_resolved=r.get("bugs_resolved"),
            deployed_by=r.get("deployed_by"),
            created_at=str(r.get("created_at", "")),
        )
        for r in (result.data or [])
    ]


# ─── POST /admin/versions ────────────────────────────────────────────────────

@router.post("", response_model=VersionLogItem, status_code=201)
async def create_version(
    body: CreateVersionRequest,
    user: CurrentUser = Depends(require_role(["org_admin"])),
):
    """
    Create a new version_log entry.

    Auth: org_admin ONLY.
    Validates version_tag format (vX.Y.Z or vX.Y.Z-beta).
    Sets deployed_by to current user.
    """
    client = get_supabase_client()

    row = {
        "version_tag": body.version_tag,
        "deployed_by": user.id,
    }
    if body.release_notes:
        row["release_notes"] = body.release_notes
    if body.breaking_changes:
        row["breaking_changes"] = body.breaking_changes
    if body.bugs_resolved:
        row["bugs_resolved"] = body.bugs_resolved

    try:
        result = client.table("version_log").insert(row).execute()
    except Exception as e:
        raise HTTPException(500, f"Failed to create version: {str(e)[:200]}")

    if not result.data:
        raise HTTPException(500, "Failed to create version — no data returned.")

    created = result.data[0]
    return VersionLogItem(
        id=created["id"],
        version_tag=created["version_tag"],
        release_date=str(created.get("release_date", "")) if created.get("release_date") else None,
        release_notes=created.get("release_notes"),
        breaking_changes=created.get("breaking_changes"),
        bugs_resolved=created.get("bugs_resolved"),
        deployed_by=created.get("deployed_by"),
        created_at=str(created.get("created_at", "")),
    )


# ─── GET /admin/versions/export ──────────────────────────────────────────────

@router.get("/export")
async def export_versions(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
):
    """Export version history as CSV (streaming)."""
    client = get_supabase_client()

    try:
        result = (
            client.table("version_log")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        versions = result.data or []
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)

        columns = [
            "id", "version_tag", "release_date", "release_notes",
            "breaking_changes", "bugs_resolved", "deployed_by", "created_at",
        ]
        writer.writerow(columns)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for v in versions:
            row = [
                v.get("id", ""),
                v.get("version_tag", ""),
                str(v.get("release_date", "")) if v.get("release_date") else "",
                v.get("release_notes", "") or "",
                v.get("breaking_changes", "") or "",
                ",".join(v.get("bugs_resolved") or []),
                v.get("deployed_by", "") or "",
                str(v.get("created_at", "")) if v.get("created_at") else "",
            ]
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=version_history.csv"},
    )


# ─── GitHub Helpers ──────────────────────────────────────────────────────────

async def _github_get(path: str) -> list[dict]:
    """Make authenticated GET request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    url = f"https://api.github.com/repos/{GITHUB_REPO}{path}"
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()


def _extract_version_from_pr(pr_title: str, pr_number: int) -> str:
    """
    Extract or generate a version tag from a PR title.
    If title contains a version pattern, use it.
    Otherwise generate a build-style version tag.
    """
    # Look for version patterns in PR title
    match = re.search(r'v?\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?', pr_title)
    if match:
        tag = match.group(0)
        if not tag.startswith("v"):
            tag = f"v{tag}"
        return tag
    
    # Generate from PR number and date
    now = datetime.now(timezone.utc)
    return f"v0.{now.strftime('%y%m%d')}.{pr_number}"


def _summarize_pr_body(body: str | None, max_len: int = 2000) -> str:
    """Clean up PR body for display as release notes."""
    if not body:
        return ""
    
    # Remove common PR template sections that aren't useful for changelog
    lines = body.split("\n")
    cleaned = []
    skip_section = False
    
    for line in lines:
        lower = line.lower().strip()
        # Skip checklist items and template headers
        if lower.startswith("## checklist") or lower.startswith("## testing"):
            skip_section = True
            continue
        if lower.startswith("## ") and skip_section:
            skip_section = False
        if skip_section:
            continue
        # Skip empty checkbox items
        if re.match(r'^\s*-\s*\[[ x]\]\s*$', line):
            continue
        cleaned.append(line)
    
    result = "\n".join(cleaned).strip()
    if len(result) > max_len:
        result = result[:max_len] + "…"
    return result


# ─── POST /admin/versions/sync-github ────────────────────────────────────────

@router.post("/sync-github", response_model=GitHubSyncResponse)
async def sync_github_versions(
    user: CurrentUser = Depends(require_role(["org_admin"])),
):
    """
    Sync version history from GitHub releases and merged PRs.
    
    Fetches:
      1. GitHub Releases (tagged versions)
      2. Recently merged PRs to main branch
    
    Creates version_log entries for any that don't already exist.
    Auth: org_admin ONLY.
    """
    client = get_supabase_client()
    
    # Get existing version tags to avoid duplicates
    try:
        existing = client.table("version_log").select("version_tag,pr_number").execute()
        existing_tags = {r["version_tag"] for r in (existing.data or [])}
        existing_prs = {r.get("pr_number") for r in (existing.data or []) if r.get("pr_number")}
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    synced_releases = 0
    synced_prs = 0
    new_versions = 0

    # ── 1. Fetch GitHub Releases ──
    try:
        releases = await _github_get("/releases?per_page=20")
        for release in releases:
            tag = release.get("tag_name", "")
            if not tag or tag in existing_tags:
                continue
            
            row = {
                "version_tag": tag,
                "release_notes": release.get("body", "")[:4000] or None,
                "release_date": release.get("published_at"),
                "deployed_by": user.id,
                "source": "github_release",
                "pr_url": release.get("html_url"),
            }
            
            try:
                client.table("version_log").insert(row).execute()
                existing_tags.add(tag)
                new_versions += 1
            except Exception as e:
                logger.warning(f"[Versions] Failed to insert release {tag}: {e}")
            
            synced_releases += 1
    except Exception as e:
        logger.warning(f"[Versions] GitHub releases fetch failed: {e}")

    # ── 2. Fetch merged PRs ──
    try:
        prs = await _github_get("/pulls?state=closed&sort=updated&direction=desc&per_page=30&base=main")
        for pr in prs:
            if not pr.get("merged_at"):
                continue  # Skip non-merged PRs
            
            pr_number = pr["number"]
            if pr_number in existing_prs:
                continue
            
            pr_title = pr.get("title", f"PR #{pr_number}")
            version_tag = _extract_version_from_pr(pr_title, pr_number)
            
            # Ensure uniqueness
            if version_tag in existing_tags:
                version_tag = f"{version_tag}-pr{pr_number}"
            
            notes = _summarize_pr_body(pr.get("body"))
            if not notes:
                notes = pr_title
            
            row = {
                "version_tag": version_tag,
                "release_notes": f"**{pr_title}**\n\n{notes}" if notes != pr_title else pr_title,
                "release_date": pr["merged_at"],
                "deployed_by": user.id,
                "source": "github_pr",
                "pr_number": pr_number,
                "pr_title": pr_title,
                "pr_url": pr.get("html_url"),
            }
            
            try:
                client.table("version_log").insert(row).execute()
                existing_tags.add(version_tag)
                existing_prs.add(pr_number)
                new_versions += 1
            except Exception as e:
                logger.warning(f"[Versions] Failed to insert PR #{pr_number}: {e}")
            
            synced_prs += 1
    except Exception as e:
        logger.warning(f"[Versions] GitHub PRs fetch failed: {e}")

    return GitHubSyncResponse(
        synced_releases=synced_releases,
        synced_prs=synced_prs,
        new_versions_created=new_versions,
        message=f"Synced {new_versions} new versions from GitHub ({synced_releases} releases, {synced_prs} PRs).",
    )


# ─── GET /admin/versions/changelog ──────────────────────────────────────────

@router.get("/changelog", response_model=list[ChangelogEntry])
async def get_changelog(
    user: CurrentUser = Depends(require_role(ADMIN_ROLES)),
    limit: int = 50,
):
    """
    Get enriched changelog with PR details. Newest first.
    Includes source type (manual, github_release, github_pr) for display.
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("version_log")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)[:200]}")

    return [
        ChangelogEntry(
            id=r["id"],
            version_tag=r["version_tag"],
            release_date=str(r.get("release_date", "")) if r.get("release_date") else None,
            release_notes=r.get("release_notes"),
            breaking_changes=r.get("breaking_changes"),
            bugs_resolved=r.get("bugs_resolved"),
            pr_number=r.get("pr_number"),
            pr_title=r.get("pr_title"),
            pr_url=r.get("pr_url"),
            source=r.get("source", "manual"),
            created_at=str(r.get("created_at", "")),
        )
        for r in (result.data or [])
    ]
