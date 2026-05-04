#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_root="${HOME}/.agents/skills"

mkdir -p "${target_root}"

for skill in auto-reading auto-learning auto-x; do
  source_path="${repo_root}/codex/skills/${skill}"
  target_path="${target_root}/${skill}"

  if [[ ! -d "${source_path}" ]]; then
    echo "Missing skill source: ${source_path}" >&2
    exit 1
  fi

  if [[ -L "${target_path}" ]]; then
    current_target="$(readlink "${target_path}")"
    if [[ "${current_target}" == "${source_path}" ]]; then
      echo "Already installed: ${skill}"
      continue
    fi
    echo "Replacing existing symlink: ${target_path}"
    rm "${target_path}"
  elif [[ -e "${target_path}" ]]; then
    echo "Refusing to overwrite non-symlink path: ${target_path}" >&2
    exit 1
  fi

  ln -s "${source_path}" "${target_path}"
  echo "Installed: ${skill} -> ${target_path}"
done

echo "Restart Codex to refresh native skill discovery."
