#!/usr/bin/env bash
set -euo pipefail

# Both build jobs call this from the repository root so their artifacts share
# one identity, including when a pull request checks out a merge commit.
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required}"
: "${GITHUB_RUN_NUMBER:?GITHUB_RUN_NUMBER is required}"
: "${GITHUB_SERVER_URL:?GITHUB_SERVER_URL is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GITHUB_EVENT_NAME:?GITHUB_EVENT_NAME is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
: "${GITHUB_STEP_SUMMARY:?GITHUB_STEP_SUMMARY is required}"
: "${SOURCE_SHA:?SOURCE_SHA is required}"
: "${SOURCE_BRANCH:?SOURCE_BRANCH is required}"

for variable in GITHUB_RUN_ID GITHUB_RUN_ATTEMPT GITHUB_RUN_NUMBER; do
  if [[ ! "${!variable}" =~ ^[0-9]+$ ]]; then
    printf '%s must contain only digits.\n' "$variable" >&2
    exit 1
  fi
done

if [[ ! "$SOURCE_SHA" =~ ^[[:xdigit:]]{40}([[:xdigit:]]{24})?$ ]]; then
  printf 'SOURCE_SHA must be a full Git commit hash.\n' >&2
  exit 1
fi

# Git refs cannot contain line breaks. Reject them in external identity values
# before writing the line-oriented metadata and GitHub environment files.
for variable in SOURCE_BRANCH GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_EVENT_NAME; do
  case "${!variable}" in
    *$'\r'*|*$'\n'*)
      printf '%s must not contain line breaks.\n' "$variable" >&2
      exit 1
      ;;
  esac
done

CHECKED_OUT_SHA="$(git rev-parse --verify HEAD)"
SHORT_SHA="${CHECKED_OUT_SHA:0:7}"
BUILD_ID="build-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${SHORT_SHA}"
RUN_URL="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
BUILT_AT="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

mkdir -p build
{
  printf 'build_id=%s\n' "$BUILD_ID"
  printf 'run_id=%s\n' "$GITHUB_RUN_ID"
  printf 'run_attempt=%s\n' "$GITHUB_RUN_ATTEMPT"
  printf 'run_number=%s\n' "$GITHUB_RUN_NUMBER"
  printf 'commit=%s\n' "$CHECKED_OUT_SHA"
  printf 'short_commit=%s\n' "$SHORT_SHA"
  printf 'source_commit=%s\n' "$SOURCE_SHA"
  printf 'branch=%s\n' "$SOURCE_BRANCH"
  printf 'event=%s\n' "$GITHUB_EVENT_NAME"
  printf 'repository=%s\n' "$GITHUB_REPOSITORY"
  printf 'run_url=%s\n' "$RUN_URL"
  printf 'created_utc=%s\n' "$BUILT_AT"
} > build/build-info.txt

{
  printf 'BUILD_ID=%s\n' "$BUILD_ID"
  printf 'SOURCE_SHA=%s\n' "$CHECKED_OUT_SHA"
  printf 'SOURCE_BRANCH=%s\n' "$SOURCE_BRANCH"
} >> "$GITHUB_ENV"
printf 'build_id=%s\n' "$BUILD_ID" >> "$GITHUB_OUTPUT"

# Escape the branch as HTML text so unusual ref characters cannot break the
# Markdown table or create links or markup in the job summary.
summary_branch() {
  local remaining="$SOURCE_BRANCH" character
  while [[ -n "$remaining" ]]; do
    character="${remaining:0:1}"
    remaining="${remaining:1}"
    case "$character" in
      '&') printf '&amp;' ;;
      '<') printf '&lt;' ;;
      '>') printf '&gt;' ;;
      '|') printf '&#124;' ;;
      '`') printf '&#96;' ;;
      '\') printf '&#92;' ;;
      *) printf '%s' "$character" ;;
    esac
  done
}

{
  printf '### Build traceability\n\n'
  printf '| Field | Value |\n| --- | --- |\n'
  printf '| Build ID | `%s` |\n' "$BUILD_ID"
  printf '| Checked-out commit | `%s` |\n' "$CHECKED_OUT_SHA"
  printf '| Source / PR head commit | `%s` |\n' "$SOURCE_SHA"
  printf '| Source branch | <code>%s</code> |\n' "$(summary_branch)"
  printf '| Run attempt | `%s` |\n' "$GITHUB_RUN_ATTEMPT"
  printf '| Created (UTC) | %s |\n' "$BUILT_AT"
  printf '| Run | %s |\n' "$RUN_URL"
} >> "$GITHUB_STEP_SUMMARY"

printf 'Build ID: %s\nChecked-out commit: %s\nSource / PR head commit: %s\nRun: %s\n' \
  "$BUILD_ID" "$CHECKED_OUT_SHA" "$SOURCE_SHA" "$RUN_URL"
