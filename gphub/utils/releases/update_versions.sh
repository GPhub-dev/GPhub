#!/usr/bin/env bash
# Refresh Version[0] of every data/libraries/*.yaml from the latest GitHub
# release (fallback: newest tag), the way the old fetch_versions.py did.
#
# Needs: gh (GH_TOKEN in CI, `gh auth login` locally), yq (mikefarah v4), jq.
# Run from anywhere:  ./gphub/utils/releases/update_versions.sh
# Non-GitHub repositories and repositories without releases or tags are skipped.
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> gphub/

lower() { tr '[:upper:]' '[:lower:]' <<<"$1"; }

for f in data/libraries/*.yaml; do
  name=$(basename "$f" .yaml)
  repo=$(yq -r '.Repository[0].Name // ""' "$f")
  url=$(yq -r '.Repository[0].URL // ""' "$f")
  case "$url" in
    https://github.com/*) ;;
    *) echo "skip $name: repository not on GitHub"; continue ;;
  esac

  if ! meta=$(gh api "repos/$repo" 2>/dev/null); then
    echo "::warning file=$f::repository $repo not found"; continue
  fi
  full=$(jq -r .full_name <<<"$meta")
  if [ "$(lower "$full")" != "$(lower "$repo")" ]; then
    echo "::warning file=$f::repository renamed: $repo -> $full (update Repository.Name/URL by hand)"
  fi
  if [ "$(jq -r .archived <<<"$meta")" = "true" ]; then
    echo "::notice file=$f::repository $repo is archived"
  fi

  if rel=$(gh api "repos/$repo/releases/latest" 2>/dev/null); then
    tag=$(jq -r .tag_name <<<"$rel")
    link=$(jq -r .html_url <<<"$rel")
  else
    tag=$(gh api "repos/$repo/tags?per_page=1" --jq '.[0].name // empty' 2>/dev/null || true)
    if [ -z "$tag" ]; then echo "skip $name: no release and no tag"; continue; fi
    link="https://github.com/$repo/releases/tag/$tag"
  fi

  current=$(yq -r '.Version[0].Name // ""' "$f")
  TAG="$tag" LINK="$link" yq -i '.Version[0].Name = strenv(TAG) | .Version[0].URL = strenv(LINK)' "$f"
  if [ "$current" != "$tag" ]; then echo "$name: $current -> $tag"; fi
done
