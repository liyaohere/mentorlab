#!/bin/bash
# Structural lints for MentorLab codebase
# Run: ./scripts/lint-structure.sh
# Purpose: Encode architectural taste so agents don't drift.
# Error messages are written to be agent-readable remediation instructions.

set -e
ERRORS=0
FRONTEND="backend/static/app/index.html"
BACKEND="backend/app"

echo "=== MentorLab Structural Lints ==="

# --- Frontend lints ---

# 1. Single-file frontend constraint
FRONTEND_FILES=$(find backend/static/app -name "*.html" -o -name "*.js" -o -name "*.css" | wc -l | tr -d ' ')
if [ "$FRONTEND_FILES" -gt 1 ]; then
  echo "FAIL: Frontend must be a single file ($FRONTEND). Found $FRONTEND_FILES files."
  echo "  FIX: Move all HTML/CSS/JS into $FRONTEND. Do not create separate .js or .css files."
  ERRORS=$((ERRORS + 1))
fi

# 2. State machine must be used for input transitions
if grep -q "switchToVoice\|switchToText" "$FRONTEND" && ! grep -q "setInputState" "$FRONTEND"; then
  echo "FAIL: Input state transitions must use setInputState(), not direct display toggling."
  echo "  FIX: See docs/design-decisions/001-input-state-machine.md"
  ERRORS=$((ERRORS + 1))
fi

# 3. input_method must not be hardcoded to 'text'
if grep -q "input_method: 'text'" "$FRONTEND" | grep -v "lastInputMethod\|methodForThisMsg" >/dev/null 2>&1; then
  HARDCODED=$(grep -n "input_method: 'text'" "$FRONTEND" | grep -v "lastInputMethod\|methodForThisMsg")
  if [ -n "$HARDCODED" ]; then
    echo "FAIL: input_method is hardcoded to 'text'. Voice messages must be tracked as 'voice'."
    echo "  FIX: Use lastInputMethod variable. See docs/design-decisions/002-input-method-tracking.md"
    echo "  Lines: $HARDCODED"
    ERRORS=$((ERRORS + 1))
  fi
fi

# 4. Frontend file size check (warn if > 800 lines)
LINES=$(wc -l < "$FRONTEND" | tr -d ' ')
if [ "$LINES" -gt 800 ]; then
  echo "WARN: $FRONTEND is $LINES lines. Consider if complexity is justified for a single-file app."
fi

# --- Backend lints ---

# 5. All routers must validate content types with base type (strip codec params)
if grep -rq "audio.content_type.*not in" "$BACKEND/routers/" 2>/dev/null; then
  if ! grep -rq "split.*;" "$BACKEND/routers/voice.py" 2>/dev/null; then
    echo "FAIL: voice.py must strip codec parameters before content-type validation."
    echo "  FIX: Use audio.content_type.split(';')[0].strip() before checking ALLOWED_AUDIO_TYPES."
    echo "  See docs/design-decisions/004-audio-format-detection.md"
    ERRORS=$((ERRORS + 1))
  fi
fi

# 6. No secrets in committed files
if grep -rq "OPENAI_API_KEY\s*=\s*sk-" "$BACKEND" --include="*.py" 2>/dev/null; then
  echo "FAIL: Hardcoded API key found in Python source."
  echo "  FIX: Use environment variables via app/config.py Settings class."
  ERRORS=$((ERRORS + 1))
fi

# --- Admin API lints ---

# 8. Export endpoints must accept admin_key query param (for <a> tag downloads)
if grep -rq "require_admin" "$BACKEND/middleware/admin_auth.py" 2>/dev/null; then
  if ! grep -q "query_params" "$BACKEND/middleware/admin_auth.py" 2>/dev/null; then
    echo "FAIL: admin_auth.py must accept admin_key as query param for download links."
    echo "  FIX: Add request.query_params.get('admin_key') fallback in require_admin()."
    ERRORS=$((ERRORS + 1))
  fi
fi

# --- Docs lints ---

# 7. Design decisions must have required fields
for f in docs/design-decisions/*.md; do
  [ -f "$f" ] || continue
  if ! grep -qF "**Date**:" "$f"; then
    echo "FAIL: $f missing **Date** field."
    echo "  FIX: Add '**Date**: YYYY-MM-DD' near the top of the file."
    ERRORS=$((ERRORS + 1))
  fi
  if ! grep -qF "**Status**:" "$f"; then
    echo "FAIL: $f missing **Status** field."
    echo "  FIX: Add '**Status**: Proposed|Implemented|Deprecated' near the top."
    ERRORS=$((ERRORS + 1))
  fi
done

# --- Summary ---
echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS structural lint(s) failed."
  exit 1
else
  echo "PASSED: All structural lints passed. ($LINES lines in frontend)"
  exit 0
fi
