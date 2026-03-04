#!/usr/bin/env bash
#
# Run the Next.js bundle analyser.
#
# Usage:
#   ./scripts/analyze.sh
#
# Opens an interactive report in the browser showing client and server
# bundle sizes.

set -euo pipefail

ANALYZE=true npx next build
