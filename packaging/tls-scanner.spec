Name:           tls-scanner
Version:        1.0.0
Release:        1%{?dist}
Summary:        Scan active TLS connections and show the owning process

License:        MIT
URL:            https://example.com/tls-scanner
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3
BuildRequires:  python3-devel

Requires:       python3
Requires:       python3-psutil

%description
tls-scanner enumerates established TCP connections on the local machine,
filters them to well-known TLS ports (or all ports), maps each connection to
its owning process, and optionally probes the remote endpoint with a new TLS
handshake to retrieve the negotiated protocol version, cipher suite, and
certificate details.

The TLS probe opens a new connection to the remote host and port; it does not
intercept or modify existing traffic. Run as root for full visibility of
connections owned by other users' processes.

%prep
%setup -q

%build
# Nothing to compile; this is a single-file Python application.

%install
rm -rf %{buildroot}

# Install the application script into libexecdir.
install -d -m 0755 %{buildroot}%{_libexecdir}/%{name}
install -m 0644 tls_scanner.py %{buildroot}%{_libexecdir}/%{name}/tls_scanner.py

# Install the launcher into bindir.
#
# Rather than hardcoding a single interpreter at build time (which can point at
# a Python that does not have the RPM-provided psutil visible), the launcher
# probes candidate interpreters at runtime and picks the first one that can
# actually import psutil. python3-psutil (the RPM dependency) installs into the
# RHEL platform Python, so that interpreter is tried first.
install -d -m 0755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/%{name} <<'EOF'
#!/bin/sh
# Locate a Python 3 interpreter that can import psutil.
SCRIPT="%{_libexecdir}/%{name}/tls_scanner.py"
for PY in /usr/libexec/platform-python /usr/bin/python3 python3; do
    if command -v "$PY" >/dev/null 2>&1 && \
       "$PY" -c 'import psutil' >/dev/null 2>&1; then
        exec "$PY" "$SCRIPT" "$@"
    fi
done

# No interpreter with psutil found; fall back to the platform Python so the
# script's own error message (which reports the interpreter path) is shown.
if command -v /usr/libexec/platform-python >/dev/null 2>&1; then
    exec /usr/libexec/platform-python "$SCRIPT" "$@"
fi
exec python3 "$SCRIPT" "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/%{name}

# Install the man page.
install -d -m 0755 %{buildroot}%{_mandir}/man1
install -m 0644 packaging/%{name}.1 %{buildroot}%{_mandir}/man1/%{name}.1

%files
%license LICENSE
%doc README.md
%{_bindir}/%{name}
%dir %{_libexecdir}/%{name}
%{_libexecdir}/%{name}/tls_scanner.py
%{_mandir}/man1/%{name}.1*

%changelog
* Tue Oct 20 2026 Packaging <packaging@example.com> - 1.0.0-1
- Initial RPM packaging of tls-scanner.
