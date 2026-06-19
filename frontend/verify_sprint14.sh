#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# verify_sprint14.sh — Sprint 14 Media Pipeline Verification
# Run: cd frontend && bash verify_sprint14.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PASS=0; FAIL=0; TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
    printf "  ✅  %s\n" "$desc"
  else
    FAIL=$((FAIL + 1))
    printf "  ❌  %s\n" "$desc"
  fi
}

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Sprint 14 — Media Pipeline  Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ─── Backend: Feature Flags ──────────────────────────────────────────────────

echo "── Backend: Feature Flags ──"
check "feature_flags.py exists" test -f ../backend/app/core/feature_flags.py
check "check_feature() defined" grep -q "async def check_feature" ../backend/app/core/feature_flags.py
check "require_feature() defined" grep -q "async def require_feature" ../backend/app/core/feature_flags.py
check "clear_feature_cache() defined" grep -q "def clear_feature_cache" ../backend/app/core/feature_flags.py
check "60-second cache TTL" grep -q "CACHE_TTL = 60" ../backend/app/core/feature_flags.py
check "_is_truthy() helper" grep -q "def _is_truthy" ../backend/app/core/feature_flags.py

# ─── Backend: Workers ────────────────────────────────────────────────────────

echo ""
echo "── Backend: Workers ──"
check "workers/settings.py exists" test -f ../backend/app/workers/settings.py
check "WorkerSettings class" grep -q "class WorkerSettings" ../backend/app/workers/settings.py
check "max_jobs=3" grep -q "max_jobs.*=.*3" ../backend/app/workers/settings.py
check "job_timeout=600" grep -q "job_timeout.*=.*600" ../backend/app/workers/settings.py
check "workers/run_worker.py exists" test -f ../backend/app/workers/run_worker.py
check "workers/video_worker.py exists" test -f ../backend/app/workers/video_worker.py
check "process_video function" grep -q "async def process_video" ../backend/app/workers/video_worker.py
check "_analyze_frame_batch function" grep -q "def _analyze_frame_batch" ../backend/app/workers/video_worker.py
check "_aggregate_video_findings function" grep -q "def _aggregate_video_findings" ../backend/app/workers/video_worker.py
check "_apply_governance_to_text function" grep -q "async def _apply_governance_to_text" ../backend/app/workers/video_worker.py
check "ffmpeg frame extraction" grep -q "ffmpeg" ../backend/app/workers/video_worker.py
check "tmp cleanup in finally block" grep -q "finally:" ../backend/app/workers/video_worker.py

# ─── Backend: Media API ──────────────────────────────────────────────────────

echo ""
echo "── Backend: Media API ──"
check "api/media.py exists" test -f ../backend/app/api/media.py
check "POST /media/analyze-image endpoint" grep -q "analyze-image" ../backend/app/api/media.py
check "POST /media/analyze-video endpoint" grep -q "analyze-video" ../backend/app/api/media.py
check "GET /media/jobs/{job_id} endpoint" grep -q "jobs/{job_id}" ../backend/app/api/media.py
check "MEDIA_ROLES defined" grep -q 'MEDIA_ROLES.*=.*\[' ../backend/app/api/media.py
check "consultant in MEDIA_ROLES" grep -q '"consultant"' ../backend/app/api/media.py
check "technician in MEDIA_ROLES" grep -q '"technician"' ../backend/app/api/media.py
check "VISION_PROMPTS dict" grep -q "VISION_PROMPTS" ../backend/app/api/media.py
check "teat_condition prompt" grep -q "teat_condition" ../backend/app/api/media.py
check "equipment prompt" grep -q '"equipment"' ../backend/app/api/media.py
check "parlor prompt" grep -q '"parlor"' ../backend/app/api/media.py
check "general prompt" grep -q '"general"' ../backend/app/api/media.py
check "HEIC to JPEG conversion" grep -q "image/heic" ../backend/app/api/media.py
check "10MB image limit" grep -q "10.*1024.*1024" ../backend/app/api/media.py
check "500MB video limit" grep -q "500.*1024.*1024" ../backend/app/api/media.py
check "Claude Vision model" grep -q "claude-sonnet-4" ../backend/app/api/media.py
check "Governance check on output" grep -q "product_mentions" ../backend/app/api/media.py
check "Sellability check" grep -q "product_sellability" ../backend/app/api/media.py
check "Feature gate on image" grep -q 'require_feature.*"feature.video_upload"' ../backend/app/api/media.py
check "ARQ job enqueue" grep -q "enqueue_job" ../backend/app/api/media.py
check "Owner check on jobs" grep -q "user_id.*!=.*user.id" ../backend/app/api/media.py
check "ImageAnalysisResponse model" grep -q "class ImageAnalysisResponse" ../backend/app/api/media.py
check "VideoUploadResponse model" grep -q "class VideoUploadResponse" ../backend/app/api/media.py
check "MediaJobResponse model" grep -q "class MediaJobResponse" ../backend/app/api/media.py
check "teat_scores in response" grep -q "teat_scores" ../backend/app/api/media.py
check "Audit logging for image" grep -q "image_analysis" ../backend/app/api/media.py
check "Audit logging for video" grep -q "video_upload" ../backend/app/api/media.py

# ─── Backend: Infrastructure ─────────────────────────────────────────────────

echo ""
echo "── Backend: Infrastructure ──"
check "Migration 005_media_jobs.sql exists" test -f ../backend/scripts/migrations/005_media_jobs.sql
check "media_jobs table DDL" grep -q "CREATE TABLE.*media_jobs" ../backend/scripts/migrations/005_media_jobs.sql
check "Procfile has worker" grep -q "worker:" ../backend/Procfile
check "requirements.txt has redis" grep -q "redis" ../backend/requirements.txt
check "requirements.txt has python-multipart" grep -q "python-multipart" ../backend/requirements.txt
check "requirements.txt has Pillow" grep -q "Pillow" ../backend/requirements.txt
check "media_router in main.py" grep -q "media_router\|media" ../backend/app/main.py
check "download_to_file in storage_service" grep -q "download_to_file" ../backend/app/services/storage_service.py

# ─── Backend: Tests ──────────────────────────────────────────────────────────

echo ""
echo "── Backend: Tests ──"
check "test_media.py exists" test -f ../backend/app/tests/test_media.py
check "TestFeatureGate class" grep -q "class TestFeatureGate" ../backend/app/tests/test_media.py
check "TestImageValidation class" grep -q "class TestImageValidation" ../backend/app/tests/test_media.py
check "TestImageAnalysis class" grep -q "class TestImageAnalysis" ../backend/app/tests/test_media.py
check "TestVideoUpload class" grep -q "class TestVideoUpload" ../backend/app/tests/test_media.py
check "TestCustomerBlocked class" grep -q "class TestCustomerBlocked" ../backend/app/tests/test_media.py
check "TestJobStatus class" grep -q "class TestJobStatus" ../backend/app/tests/test_media.py
check "TestFeatureFlagCache class" grep -q "class TestFeatureFlagCache" ../backend/app/tests/test_media.py
check "8+ test methods" test "$(grep -c "def test_" ../backend/app/tests/test_media.py)" -ge 8

# ─── Frontend: API Types ─────────────────────────────────────────────────────

echo ""
echo "── Frontend: API Types & Functions ──"
check "ImageAnalysisResponse type" grep -q "ImageAnalysisResponse" src/lib/api.ts
check "VideoUploadResponse type" grep -q "VideoUploadResponse" src/lib/api.ts
check "MediaJobResponse type" grep -q "MediaJobResponse" src/lib/api.ts
check "analyzeImage function" grep -q "async function analyzeImage" src/lib/api.ts
check "uploadVideo function" grep -q "async function uploadVideo" src/lib/api.ts
check "fetchMediaJob function" grep -q "async function fetchMediaJob" src/lib/api.ts
check "checkFeatureEnabled function" grep -q "async function checkFeatureEnabled" src/lib/api.ts
check "analyzeImage uses FormData" grep -A15 "analyzeImage" src/lib/api.ts | grep -q "FormData"
check "uploadVideo uses FormData" grep -A15 "uploadVideo" src/lib/api.ts | grep -q "FormData"

# ─── Frontend: ChatInput ─────────────────────────────────────────────────────

echo ""
echo "── Frontend: ChatInput ──"
check "ChatInput.tsx has onFileSelect prop" grep -q "onFileSelect" src/components/chat/ChatInput.tsx
check "ChatInput.tsx has selectedFile prop" grep -q "selectedFile" src/components/chat/ChatInput.tsx
check "ChatInput.tsx has onFileClear prop" grep -q "onFileClear" src/components/chat/ChatInput.tsx
check "ChatInput.tsx has mediaEnabled prop" grep -q "mediaEnabled" src/components/chat/ChatInput.tsx
check "Paperclip import" grep -q "Paperclip" src/components/chat/ChatInput.tsx
check "Hidden file input" grep -q 'type="file"' src/components/chat/ChatInput.tsx
check "ACCEPTED_TYPES constant" grep -q "ACCEPTED_TYPES" src/components/chat/ChatInput.tsx
check "File size validation" grep -q "MAX_IMAGE_MB\|MAX_VIDEO_MB" src/components/chat/ChatInput.tsx
check "canSend includes file" grep -q "selectedFile" src/components/chat/ChatInput.tsx
check "File preview with name" grep -q "selectedFile.name" src/components/chat/ChatInput.tsx
check "48px tap target on paperclip" grep -q "h-12 w-12" src/components/chat/ChatInput.tsx

# ─── Frontend: ChatPage ──────────────────────────────────────────────────────

echo ""
echo "── Frontend: ChatPage ──"
check "ChatPage imports analyzeImage" grep -q "analyzeImage" src/pages/ChatPage.tsx
check "ChatPage imports uploadVideo" grep -q "uploadVideo" src/pages/ChatPage.tsx
check "ChatPage imports checkFeatureEnabled" grep -q "checkFeatureEnabled" src/pages/ChatPage.tsx
check "ChatPage imports useAuthStore" grep -q "useAuthStore" src/pages/ChatPage.tsx
check "ChatPage imports useNavigate" grep -q "useNavigate" src/pages/ChatPage.tsx
check "MEDIA_ROLES constant" grep -q "MEDIA_ROLES" src/pages/ChatPage.tsx
check "selectedFile state" grep -q "useState.*File.*null" src/pages/ChatPage.tsx
check "mediaEnabled state" grep -q "mediaEnabled.*setMediaEnabled" src/pages/ChatPage.tsx
check "mediaUploading state" grep -q "mediaUploading.*setMediaUploading" src/pages/ChatPage.tsx
check "Feature flag check on mount" grep -q "checkFeatureEnabled.*feature.video_upload" src/pages/ChatPage.tsx
check "Image analysis handler" grep -q "analyzeImage(file" src/pages/ChatPage.tsx
check "Video upload handler" grep -q "uploadVideo(file)" src/pages/ChatPage.tsx
check "Navigate to job status" grep -q "/media/jobs/" src/pages/ChatPage.tsx
check "ChatInput mediaEnabled prop passed" grep -q "mediaEnabled={mediaEnabled}" src/pages/ChatPage.tsx
check "ChatInput onFileSelect prop passed" grep -q "onFileSelect={handleFileSelect}" src/pages/ChatPage.tsx

# ─── Frontend: MediaJobStatusPage ────────────────────────────────────────────

echo ""
echo "── Frontend: MediaJobStatusPage ──"
check "MediaJobStatusPage.tsx exists" test -f src/pages/media/MediaJobStatusPage.tsx
check "10-second poll interval" grep -q "10_000\|10000" src/pages/media/MediaJobStatusPage.tsx
check "useParams for jobId" grep -q "useParams" src/pages/media/MediaJobStatusPage.tsx
check "fetchMediaJob call" grep -q "fetchMediaJob" src/pages/media/MediaJobStatusPage.tsx
check "setInterval for polling" grep -q "setInterval" src/pages/media/MediaJobStatusPage.tsx
check "clearInterval on cleanup" grep -q "clearInterval" src/pages/media/MediaJobStatusPage.tsx
check "Processing status display" grep -q "processing\|Analyzing" src/pages/media/MediaJobStatusPage.tsx
check "Complete status display" grep -q "complete\|Complete" src/pages/media/MediaJobStatusPage.tsx
check "Failed status display" grep -q "failed\|Failed" src/pages/media/MediaJobStatusPage.tsx
check "View Report link" grep -q "View Report" src/pages/media/MediaJobStatusPage.tsx
check "Link to report preview" grep -q "reports.*preview" src/pages/media/MediaJobStatusPage.tsx
check "Frames extracted display" grep -q "frames_extracted\|Frames Extracted" src/pages/media/MediaJobStatusPage.tsx
check "Frames analyzed display" grep -q "frames_analyzed\|Frames Analyzed" src/pages/media/MediaJobStatusPage.tsx
check "Back to Chat button" grep -q "Back to Chat" src/pages/media/MediaJobStatusPage.tsx

# ─── Frontend: Routes ────────────────────────────────────────────────────────

echo ""
echo "── Frontend: Routes ──"
check "MediaJobStatusPage import in App.tsx" grep -q "MediaJobStatusPage" src/App.tsx
check "media/jobs/:jobId route" grep -q "media/jobs/:jobId" src/App.tsx
check "Route inside CustomerGuard" awk '/CustomerGuard/,/\/Route>/{if(/MediaJobStatusPage/) found=1} END{exit !found}' src/App.tsx

# ─── Frontend: Tests ─────────────────────────────────────────────────────────

echo ""
echo "── Frontend: Tests ──"
check "MediaPipeline.test.tsx exists" test -f src/pages/media/__tests__/MediaPipeline.test.tsx
check "8 test blocks" test "$(grep -c "test(" src/pages/media/__tests__/MediaPipeline.test.tsx)" -ge 8
check "ChatInput paperclip tests" grep -q "paperclip" src/pages/media/__tests__/MediaPipeline.test.tsx
check "ChatInput file preview test" grep -q "file preview" src/pages/media/__tests__/MediaPipeline.test.tsx
check "Feature flag test" grep -q "feature flag" src/pages/media/__tests__/MediaPipeline.test.tsx
check "MediaJobStatusPage tests" grep -q "MediaJobStatusPage" src/pages/media/__tests__/MediaPipeline.test.tsx
check "View Report link test" grep -q "View Report" src/pages/media/__tests__/MediaPipeline.test.tsx

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════════"
printf "  Results: %d / %d passed" "$PASS" "$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  printf "  (%d FAILED)" "$FAIL"
fi
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

exit "$FAIL"
