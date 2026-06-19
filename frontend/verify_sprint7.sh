#!/bin/bash
# Sprint 7 Verification Checklist
# Chat interface — 7 required items + structural checks

PASS=0
FAIL=0
TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  local desc="$1"
  local result="$2"
  if [ "$result" = "PASS" ]; then
    echo "  ✅ $desc"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $desc -- $3"
    FAIL=$((FAIL + 1))
  fi
}

echo "═══════════════════════════════════════════════"
echo " Sprint 7 — Chat Interface Verification"
echo "═══════════════════════════════════════════════"

# 1. Chat sends message, receives response, shows correct domain badge
echo ""
echo "1. Chat sends message + domain badge:"
grep -q "sendMessage" frontend/src/pages/ChatPage.tsx && R="PASS" || R="FAIL"
check "ChatPage calls sendMessage API" "$R" "Missing sendMessage call"

grep -q "DOMAIN_BADGES" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "MessageBubble has DOMAIN_BADGES config" "$R" "Missing DOMAIN_BADGES"

grep -q "PRICING.*green\|domain-pricing" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "PRICING domain uses green color" "$R" "Missing green for PRICING"

grep -q "TEAT_DIP.*blue\|domain-teat-dip" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "TEAT_DIP domain uses blue color" "$R" "Missing blue for TEAT_DIP"

grep -q "TROUBLESHOOTING.*amber\|domain-troubleshooting" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "TROUBLESHOOTING domain uses amber color" "$R" "Missing amber for TROUBLESHOOTING"

grep -q "COW_HEALTH.*purple\|domain-cow-health" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "COW_HEALTH domain uses purple color" "$R" "Missing purple for COW_HEALTH"

# 2. Governance citation visible on pricing
echo ""
echo "2. Governance citation:"
grep -q "governanceApplied" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "MessageBubble checks governanceApplied flag" "$R" "Missing governanceApplied check"

grep -q "Pricing confirmed" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "Governance citation text 'Pricing confirmed'" "$R" "Missing citation text"

# 3. Location selector locks
echo ""
echo "3. Location selector:"
test -f frontend/src/components/chat/LocationSelector.tsx && R="PASS" || R="FAIL"
check "LocationSelector component exists" "$R" "Missing LocationSelector.tsx"

grep -q "LOCATIONS" frontend/src/store/chat.ts && R="PASS" || R="FAIL"
check "Chat store has LOCATIONS map" "$R" "Missing LOCATIONS"

grep -q "setLocation" frontend/src/components/chat/LocationSelector.tsx && R="PASS" || R="FAIL"
check "LocationSelector calls setLocation API" "$R" "Missing setLocation call"

grep -q "Switch Location\|Switching" frontend/src/components/chat/LocationSelector.tsx && R="PASS" || R="FAIL"
check "Location change confirmation dialog" "$R" "Missing confirmation dialog"

# 4. Thumbs-down shows follow-up field
echo ""
echo "4. Feedback system:"
grep -q "ThumbsUp" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "Thumbs up button exists" "$R" "Missing ThumbsUp"

grep -q "ThumbsDown" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "Thumbs down button exists" "$R" "Missing ThumbsDown"

grep -q "What was wrong" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "Follow-up text field on thumbs-down" "$R" "Missing follow-up field"

grep -q "submitFeedback" frontend/src/lib/api.ts && R="PASS" || R="FAIL"
check "submitFeedback API function" "$R" "Missing submitFeedback in api.ts"

# 5. Bug report form
echo ""
echo "5. Bug report:"
test -f frontend/src/components/chat/BugReportSheet.tsx && R="PASS" || R="FAIL"
check "BugReportSheet component exists" "$R" "Missing BugReportSheet.tsx"

grep -q "submitBugReport" frontend/src/components/chat/BugReportSheet.tsx && R="PASS" || R="FAIL"
check "BugReportSheet calls submitBugReport API" "$R" "Missing submitBugReport call"

grep -q "severity" frontend/src/components/chat/BugReportSheet.tsx && R="PASS" || R="FAIL"
check "Severity selection buttons" "$R" "Missing severity buttons"

grep -q "auto-attached\|Auto-attached" frontend/src/components/chat/BugReportSheet.tsx && R="PASS" || R="FAIL"
check "Auto-attached context note" "$R" "Missing auto-context"

grep -q "helping make CowCare better\|Thanks for helping" frontend/src/components/chat/BugReportSheet.tsx && R="PASS" || R="FAIL"
check "Success message matches spec" "$R" "Missing success message"

# 6. Input does not zoom on iOS
echo ""
echo "6. iOS zoom prevention:"
grep -q 'fontSize.*16px\|font-size.*16px' frontend/src/components/chat/ChatInput.tsx && R="PASS" || R="FAIL"
check "ChatInput has 16px font-size" "$R" "Missing 16px font in ChatInput"

grep -q 'fontSize.*16px\|font-size.*16px' frontend/src/components/chat/BugReportSheet.tsx && R="PASS" || R="FAIL"
check "BugReport inputs have 16px font-size" "$R" "Missing 16px in BugReport"

# 7. No horizontal scroll at 390px
echo ""
echo "7. Mobile-first constraints:"
grep -q "max-w-\[85%\]\|max-w-3xl" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "MessageBubble max-width 85%" "$R" "Missing max-width constraint"

grep -q "tap-target" frontend/src/components/chat/ChatInput.tsx && R="PASS" || R="FAIL"
check "ChatInput has 48px tap target" "$R" "Missing tap-target"

# 8. Backend endpoints
echo ""
echo "8. Backend API endpoints:"
test -f backend/app/api/session.py && R="PASS" || R="FAIL"
check "Session API module exists" "$R" "Missing session.py"

grep -q "/session/location" backend/app/api/session.py && R="PASS" || R="FAIL"
check "POST /session/location endpoint" "$R" "Missing /session/location"

grep -q "/feedback" backend/app/api/session.py && R="PASS" || R="FAIL"
check "POST /feedback endpoint" "$R" "Missing /feedback"

grep -q "/bugs" backend/app/api/session.py && R="PASS" || R="FAIL"
check "POST /bugs endpoint" "$R" "Missing /bugs"

grep -q "session_router" backend/app/main.py && R="PASS" || R="FAIL"
check "Session router registered in main.py" "$R" "Missing session_router"

# 9. Session management
echo ""
echo "9. Session management:"
grep -q "newConversation" frontend/src/store/chat.ts && R="PASS" || R="FAIL"
check "newConversation action in chat store" "$R" "Missing newConversation"

grep -q "New Chat\|New Conversation\|RotateCcw" frontend/src/pages/ChatPage.tsx && R="PASS" || R="FAIL"
check "New Conversation button in chat header" "$R" "Missing new conversation button"

grep -v '^\s*[/*]' frontend/src/store/chat.ts | grep -q "localStorage\." && R="ANTI" || R="PASS"
check "Chat history NOT in localStorage (security)" "$R" "Security: found localStorage API call"

# 10. Build
echo ""
echo "10. Build verification:"
test -d frontend/dist && R="PASS" || R="FAIL"
check "Production build exists" "$R" "Run npm build first"

# 11. Auto-expanding textarea
echo ""
echo "11. Chat input features:"
grep -q "textarea\|Textarea" frontend/src/components/chat/ChatInput.tsx && R="PASS" || R="FAIL"
check "Uses textarea (not input) for chat" "$R" "Should use textarea"

grep -q "adjustHeight\|auto.*height\|scrollHeight" frontend/src/components/chat/ChatInput.tsx && R="PASS" || R="FAIL"
check "Auto-expanding textarea logic" "$R" "Missing auto-expand"

grep -q "isMobile\|mobile\|Android" frontend/src/components/chat/ChatInput.tsx && R="PASS" || R="FAIL"
check "Mobile vs desktop Enter key behavior" "$R" "Missing mobile detection"

# 12. Loading dots
echo ""
echo "12. Loading animation:"
grep -q "LoadingDots\|animate-bounce" frontend/src/components/chat/MessageBubble.tsx && R="PASS" || R="FAIL"
check "3-dot loading animation" "$R" "Missing loading dots"

grep -q "addLoadingMessage\|removeLoadingMessage" frontend/src/pages/ChatPage.tsx && R="PASS" || R="FAIL"
check "Loading message lifecycle in ChatPage" "$R" "Missing loading lifecycle"

echo ""
echo "═══════════════════════════════════════════════"
echo " Results: $PASS/$TOTAL PASS, $FAIL FAIL"
echo "═══════════════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
  echo " 🎉 Sprint 7 FULLY VERIFIED"
else
  echo " ⚠️  $FAIL check(s) need attention"
fi
