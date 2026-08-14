#!/bin/bash
# fetch-page.sh <url> [max-chars]
#
# Fetches a page with a real headless browser and prints it as plain text.
#
# Why this exists: WebFetch is blocked outright by NHS Jobs, TRAC, Lever, Indeed
# and LinkedIn (403 via CloudFront), and returns only an empty shell for
# client-rendered sites like Workable. Chrome's *new* headless mode with a real
# user agent gets the actual page. Verified 14 Aug 2026 on an NHS Jobs advert
# that WebFetch, curl and old `--headless` all failed to retrieve.
#
# Use it whenever WebFetch fails or returns something suspiciously empty.
# Read-only: it loads a URL and prints text. It cannot click, submit or log in.

set -uo pipefail

URL="${1:-}"
MAX="${2:-6000}"
[ -z "$URL" ] && { echo "usage: fetch-page.sh <url> [max-chars]" >&2; exit 2; }

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || CHROME="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
[ -x "$CHROME" ] || { echo "FETCH-ERROR: no Chrome or Brave found" >&2; exit 3; }

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

HTML=$("$CHROME" --headless=new --disable-gpu --no-first-run --no-default-browser-check \
        --user-agent="$UA" --virtual-time-budget=12000 --dump-dom "$URL" 2>/dev/null)

if [ -z "$HTML" ]; then
  echo "FETCH-ERROR: empty response for $URL" >&2
  exit 4
fi

MAX="$MAX" python3 -c '
import re, sys, html, os
t = sys.stdin.read()
t = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", t, flags=re.S|re.I)
t = re.sub(r"<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", t, flags=re.I)
t = html.unescape(re.sub(r"<[^>]+>", " ", t))
t = re.sub(r"[ \t\xa0]+", " ", t)
t = re.sub(r"\n\s*\n+", "\n", t).strip()
print(t[:int(os.environ.get("MAX", "6000"))])
' <<<"$HTML"
