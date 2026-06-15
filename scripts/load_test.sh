#!/usr/bin/env bash
#
# Simple parallel load test for one API tier. Fires N total GET requests with
# C running concurrently, then prints the latency distribution. Use it for
# concurrency/scaling tests that Postman's sequential runner can't produce.
#
# Usage:
#   ./load_test.sh <url> [total_requests] [concurrency]
#
# Example:
#   ./load_test.sh "https://abc.execute-api.us-east-1.amazonaws.com/prod-128/products" 50 10
#
set -euo pipefail

URL="${1:?Usage: ./load_test.sh <url> [total] [concurrency]}"
TOTAL="${2:-50}"
CONCURRENCY="${3:-10}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Load test: $TOTAL requests, $CONCURRENCY concurrent -> $URL"

seq "$TOTAL" | xargs -P "$CONCURRENCY" -I {} \
  curl -s -o /dev/null -w "%{time_total}\n" "$URL" > "$TMP/times.txt"

# Convert seconds -> ms and compute stats with awk.
awk '
  { v=$1*1000; t+=v; n++; a[n]=v; if(min==""||v<min)min=v; if(v>max)max=v }
  END {
    asort(a);
    p50=a[int(n*0.50)]; p90=a[int(n*0.90)]; p99=a[int(n*0.99)];
    printf "Requests: %d\n", n;
    printf "Avg: %.1f ms | Min: %.1f ms | Max: %.1f ms\n", t/n, min, max;
    printf "p50: %.1f ms | p90: %.1f ms | p99: %.1f ms\n", p50, p90, p99;
  }
' "$TMP/times.txt"
