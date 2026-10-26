#!/usr/bin/env bash
#
# Build the tls-scanner Debian package.
#
# Usage:
#   ./packaging/build-deb.sh [output-directory]
#
# Requires dpkg-deb. The package is architecture-independent and depends on
# Debian's python3 and python3-psutil packages.

set -euo pipefail

NAME="tls-scanner"
VERSION="1.0.0"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${1:-${REPO_ROOT}/dist}"

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Error: dpkg-deb is required to build the Debian package." >&2
    exit 1
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT

PKGDIR="${STAGE}/${NAME}"
mkdir -p \
    "${PKGDIR}/DEBIAN" \
    "${PKGDIR}/usr/bin" \
    "${PKGDIR}/usr/lib/${NAME}" \
    "${PKGDIR}/usr/share/doc/${NAME}" \
    "${PKGDIR}/usr/share/man/man1"

install -m 0644 "${SCRIPT_DIR}/debian-control" "${PKGDIR}/DEBIAN/control"
install -m 0644 "${REPO_ROOT}/tls_scanner.py" \
    "${PKGDIR}/usr/lib/${NAME}/tls_scanner.py"
install -m 0644 "${REPO_ROOT}/README.md" \
    "${PKGDIR}/usr/share/doc/${NAME}/README.md"
install -m 0644 "${REPO_ROOT}/LICENSE" \
    "${PKGDIR}/usr/share/doc/${NAME}/copyright"
install -m 0644 "${SCRIPT_DIR}/${NAME}.1" \
    "${PKGDIR}/usr/share/man/man1/${NAME}.1"
gzip -9n "${PKGDIR}/usr/share/man/man1/${NAME}.1"

cat > "${PKGDIR}/usr/bin/${NAME}" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/tls-scanner/tls_scanner.py "$@"
EOF
chmod 0755 "${PKGDIR}/usr/bin/${NAME}"

mkdir -p "${OUTPUT_DIR}"
DEB_FILE="${OUTPUT_DIR}/${NAME}_${VERSION}_all.deb"
dpkg-deb --build --root-owner-group "${PKGDIR}" "${DEB_FILE}"
echo "[*] Created Debian package: ${DEB_FILE}"
