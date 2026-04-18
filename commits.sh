#!/usr/bin/env bash
set -euo pipefail

# Rewrite a recent range of commits on the current branch so that:
# - author name/email become the target identity
# - committer name/email become the target identity
# - any "Co-authored-by: Claude ..." lines are removed from commit messages
#
# Safety features:
# - refuses to run on a dirty working tree
# - only rewrites the last N commits, never the whole repo
# - creates a backup branch first
# - prints the commits it will rewrite
# - asks for confirmation unless --yes is passed
# - exits early if the target range already matches the requested identity
#
# Note:
# This rewrites published history. After review, you will need to force-push.

# -----------------------------
# Configurable defaults
# -----------------------------
DEFAULT_NAME="YOUR_NAME_HERE"
DEFAULT_EMAIL="YOUR_EMAIL_HERE"
BACKUP_PREFIX="backup/rewrite-author"

# -----------------------------
# Argument defaults
# -----------------------------
TARGET_NAME="$DEFAULT_NAME"
TARGET_EMAIL="$DEFAULT_EMAIL"
LAST_COUNT=""
ASSUME_YES=0
BACKUP_BRANCH=""

usage() {
  cat <<'EOF'
Usage:
  rewrite-recent-authors.sh --last N [--name "Your Name"] [--email "you@example.com"] [--yes]

Required:
  --last N            Rewrite only the last N commits on the current branch

Optional:
  --name NAME         Target author/committer name
  --email EMAIL       Target author/committer email
  --yes               Skip the confirmation prompt
  -h, --help          Show this help

Examples:
  ./rewrite-recent-authors.sh --last 8 --name "Jane Doe" --email "jane@example.com"
  ./rewrite-recent-authors.sh --last 5 --yes --name "Jane Doe" --email "jane@example.com"

Behavior:
  - rewrites both author and committer identity
  - removes commit-message lines matching: Co-authored-by: Claude ...
  - creates a backup branch before rewriting
  - works only from the current branch
EOF
}

die() {
  echo "Error: $*" >&2
  exit 1
}

confirm() {
  local prompt="${1:-Continue? [y/N] }"
  local reply
  read -r -p "$prompt" reply
  [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

require_clean_worktree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    die "Working tree is dirty. Commit, stash, or clean your changes before rewriting history."
  fi
}

require_git_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "This is not a Git repository."
}

require_current_branch() {
  CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  [[ -n "$CURRENT_BRANCH" ]] || die "Detached HEAD is not supported. Check out the branch you want to rewrite."
}

require_upstream() {
  UPSTREAM_REF="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
  [[ -n "$UPSTREAM_REF" ]] || die "Current branch has no upstream. Cannot print the exact force-push command."
  UPSTREAM_REMOTE="${UPSTREAM_REF%%/*}"
  UPSTREAM_BRANCH="${UPSTREAM_REF#*/}"
}

validate_args() {
  [[ -n "$LAST_COUNT" ]] || die "--last N is required."
  [[ "$LAST_COUNT" =~ ^[1-9][0-9]*$ ]] || die "--last must be a positive integer."

  [[ "$TARGET_NAME" != "YOUR_NAME_HERE" ]] || die "Set your real name with --name or by editing DEFAULT_NAME."
  [[ "$TARGET_EMAIL" != "YOUR_EMAIL_HERE" ]] || die "Set your real email with --email or by editing DEFAULT_EMAIL."
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --last)
        [[ $# -ge 2 ]] || die "--last requires a value."
        LAST_COUNT="$2"
        shift 2
        ;;
      --name)
        [[ $# -ge 2 ]] || die "--name requires a value."
        TARGET_NAME="$2"
        shift 2
        ;;
      --email)
        [[ $# -ge 2 ]] || die "--email requires a value."
        TARGET_EMAIL="$2"
        shift 2
        ;;
      --yes)
        ASSUME_YES=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

print_target_commits() {
  echo
  echo "Current branch: $CURRENT_BRANCH"
  echo "Upstream:       $UPSTREAM_REF"
  echo "Target identity:"
  echo "  Name:  $TARGET_NAME"
  echo "  Email: $TARGET_EMAIL"
  echo
  echo "Commits that will be rewritten (oldest first):"
  git log --reverse --format='  %h  %an <%ae> | %cn <%ce>%n      %s%n' "$TARGET_RANGE"
}

detect_noop() {
  local sha
  local author_name author_email committer_name committer_email body
  local needs_rewrite=0

  while IFS= read -r sha; do
    author_name="$(git show -s --format='%an' "$sha")"
    author_email="$(git show -s --format='%ae' "$sha")"
    committer_name="$(git show -s --format='%cn' "$sha")"
    committer_email="$(git show -s --format='%ce' "$sha")"
    body="$(git log -1 --format=%B "$sha")"

    if [[ "$author_name" != "$TARGET_NAME" ]] \
      || [[ "$author_email" != "$TARGET_EMAIL" ]] \
      || [[ "$committer_name" != "$TARGET_NAME" ]] \
      || [[ "$committer_email" != "$TARGET_EMAIL" ]] \
      || grep -Eiq '^[[:space:]]*Co-authored-by:[[:space:]]*Claude([[:space:]]|<|$)' <<<"$body"
    then
      needs_rewrite=1
      break
    fi
  done < <(git rev-list --reverse "$TARGET_RANGE")

  if [[ "$needs_rewrite" -eq 0 ]]; then
    echo
    echo "Nothing to rewrite in the last $LAST_COUNT commits."
    echo "They already match the requested identity and contain no Claude co-author lines."
    exit 0
  fi
}

build_message_filter() {
  TEMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TEMP_DIR"' EXIT

  MSG_FILTER_SCRIPT="$TEMP_DIR/msg-filter.sh"

  cat >"$MSG_FILTER_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

tmp_in="$(mktemp)"
trap 'rm -f "$tmp_in"' EXIT
cat >"$tmp_in"

# Remove only commit-message lines that look like:
#   Co-authored-by: Claude ...
# Case-insensitive on the "Co-authored-by" prefix, but intentionally specific
# to Claude so unrelated co-author lines are preserved.
awk '
  !/^[Cc]o-authored-by:[[:space:]]*Claude([[:space:]]|<|$)/ {
    print
  }
' "$tmp_in" | awk '
  {
    lines[NR] = $0
    if ($0 !~ /^[[:space:]]*$/) last_nonblank = NR
  }
  END {
    for (i = 1; i <= last_nonblank; i++) {
      print lines[i]
    }
  }
'
EOF

  chmod +x "$MSG_FILTER_SCRIPT"
}

set_backup_branch_name() {
  BACKUP_BRANCH="${BACKUP_PREFIX}-${CURRENT_BRANCH//\//-}-$(date +%Y%m%d-%H%M%S)"
}

make_backup_branch() {
  [[ -n "$BACKUP_BRANCH" ]] || die "Internal error: backup branch name was not initialized."
  git branch "$BACKUP_BRANCH"
  echo
  echo "Backup branch created: $BACKUP_BRANCH"
}

rewrite_history() {
  export TARGET_NAME TARGET_EMAIL

  # We rewrite only TARGET_RANGE, not the whole repo.
  # filter-branch is used here because it can reliably update both metadata and
  # commit messages in one pass over a bounded range.
  FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
    --env-filter '
      export GIT_AUTHOR_NAME="$TARGET_NAME"
      export GIT_AUTHOR_EMAIL="$TARGET_EMAIL"
      export GIT_COMMITTER_NAME="$TARGET_NAME"
      export GIT_COMMITTER_EMAIL="$TARGET_EMAIL"
    ' \
    --msg-filter "$MSG_FILTER_SCRIPT" \
    -- "$TARGET_RANGE"
}

print_post_rewrite_summary() {
  echo
  echo "Rewrite complete."
  echo
  echo "Rewritten commits now (oldest first):"
  git log --reverse --format='  %h  %an <%ae> | %cn <%ce>%n      %s%n' "HEAD~${LAST_COUNT}..HEAD"
  echo
  echo "Review tip:"
  echo "  git log --format=fuller ${BACKUP_BRANCH}..HEAD"
  echo
  echo "If everything looks correct, push with:"
  echo "  git push --force-with-lease ${UPSTREAM_REMOTE} HEAD:${UPSTREAM_BRANCH}"
}

main() {
  parse_args "$@"
  validate_args
  require_git_repo
  require_current_branch
  require_upstream
  require_clean_worktree

  local total_commits
  total_commits="$(git rev-list --count HEAD)"

  # Require a bounded recent range; do not allow rewriting the whole reachable history.
  if (( LAST_COUNT >= total_commits )); then
    die "--last $LAST_COUNT would rewrite the whole branch history or more. Choose a smaller count."
  fi

  TARGET_RANGE="HEAD~${LAST_COUNT}..HEAD"

  # Validate that the range resolves before continuing.
  git rev-parse "HEAD~${LAST_COUNT}" >/dev/null 2>&1 || die "Cannot resolve HEAD~${LAST_COUNT}."

  set_backup_branch_name
  print_target_commits
  detect_noop

  echo
  echo "This will rewrite the last $LAST_COUNT commits on '$CURRENT_BRANCH'."
  echo "A backup branch will be kept at '$BACKUP_BRANCH' once created."

  if [[ "$ASSUME_YES" -ne 1 ]]; then
    confirm "Proceed with history rewrite? [y/N] " || {
      echo "Aborted."
      exit 1
    }
  fi

  make_backup_branch
  build_message_filter
  rewrite_history
  print_post_rewrite_summary
}

main "$@"
