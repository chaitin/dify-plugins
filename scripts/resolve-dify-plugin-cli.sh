#!/usr/bin/env bash
set -euo pipefail

version="${DIFY_PLUGIN_CLI_VERSION:-0.6.3}"
cache_dir="${DIFY_PLUGIN_CLI_CACHE:-.cache/dify-plugin-cli}"

if [[ -n "${DIFY_PLUGIN_CLI:-}" ]]; then
  test -x "${DIFY_PLUGIN_CLI}"
  printf '%s\n' "${DIFY_PLUGIN_CLI}"
  exit 0
fi

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
arch="$(uname -m)"
case "${arch}" in x86_64) arch=amd64 ;; aarch64|arm64) arch=arm64 ;; *) echo "unsupported architecture: ${arch}" >&2; exit 1 ;; esac
case "${os}" in linux|darwin) ;; *) echo "unsupported operating system: ${os}" >&2; exit 1 ;; esac

asset="dify-plugin-${os}-${arch}"
case "${os}-${arch}" in
  darwin-amd64) checksum=3ccf9ee0d6a84572b791b4d3c8c77ee46f8e00d5c3c185ff0d83670b587f545a ;;
  darwin-arm64) checksum=5ad6cb53d34e737b695923a1a83ee8777c17584f79227a1bc6ed4ed0d42edfe0 ;;
  linux-amd64) checksum=fcc09adf9f98848300fe6cc6c762deb298c5ebb86dd469ac20666cda630275b2 ;;
  linux-arm64) checksum=d3bc0a3de9f77b6b1af131b64be95432ea1530286adcf0ad00ee9dbd89011b14 ;;
esac

if [[ "${version}" != "0.6.3" ]]; then
  echo "no pinned checksum for dify-plugin ${version}; set DIFY_PLUGIN_CLI to a verified binary" >&2
  exit 1
fi

target="${cache_dir}/${version}/${asset}"
if [[ ! -x "${target}" ]]; then
  mkdir -p "$(dirname "${target}")"
  temporary="${target}.download"
  curl --fail --location --retry 3 --output "${temporary}" \
    "https://github.com/langgenius/dify-plugin-daemon/releases/download/${version}/${asset}"
  printf '%s  %s\n' "${checksum}" "${temporary}" | sha256sum --check --status
  chmod 0755 "${temporary}"
  mv "${temporary}" "${target}"
fi

(cd / && printf '%s\n' "$(realpath "${OLDPWD}/${target}")")
