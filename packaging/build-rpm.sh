#!/usr/bin/env bash
#
# build-rpm.sh — build the tls-scanner RPM from this source tree.
#
# Usage:
#   ./packaging/build-rpm.sh
#
# Produces a source tarball, then builds a binary (and source) RPM under
# the rpmbuild tree. Requires: rpmbuild (rpm-build package). rpmlint is
# run automatically when available.

set -euo pipefail

NAME="tls-scanner"
VERSION="1.0.0"

# Resolve repo root (the parent of this script's directory).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SPEC="${SCRIPT_DIR}/${NAME}.spec"

# Determine the rpmbuild top directory.
TOPDIR="$(rpm --eval '%{_topdir}')"
echo "[*] rpmbuild top directory: ${TOPDIR}"

mkdir -p "${TOPDIR}"/{BUILD,BUILDROOT,RPMS,SRPMS,SOURCES,SPECS}

# Stage the sources into a versioned directory for the tarball.
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT

PKGDIR="${STAGE}/${NAME}-${VERSION}"
mkdir -p "${PKGDIR}/packaging"

cp "${REPO_ROOT}/tls_scanner.py"        "${PKGDIR}/"
cp "${REPO_ROOT}/README.md"             "${PKGDIR}/"
cp "${REPO_ROOT}/LICENSE"               "${PKGDIR}/"
cp "${REPO_ROOT}/requirements.txt"      "${PKGDIR}/"
cp "${SCRIPT_DIR}/${NAME}.1"            "${PKGDIR}/packaging/"

# Build the source tarball.
TARBALL="${TOPDIR}/SOURCES/${NAME}-${VERSION}.tar.gz"
tar -czf "${TARBALL}" -C "${STAGE}" "${NAME}-${VERSION}"
echo "[*] Created source tarball: ${TARBALL}"

# Build the RPMs.
echo "[*] Running rpmbuild..."
rpmbuild -ba "${SPEC}"

echo
echo "[*] Build complete. Artifacts:"
find "${TOPDIR}/RPMS" "${TOPDIR}/SRPMS" -name "${NAME}-${VERSION}*" -print 2>/dev/null || true

# Run rpmlint if present (non-fatal).
if command -v rpmlint >/dev/null 2>&1; then
    echo
    echo "[*] Running rpmlint..."
    RPM_FILE="$(find "${TOPDIR}/RPMS" -name "${NAME}-${VERSION}*.rpm" | head -n1)"
    rpmlint "${SPEC}" "${RPM_FILE}" || true
fi
