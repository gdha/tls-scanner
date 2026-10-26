"""
TLS Session Scanner for Windows

Scans active TCP connections on well-known TLS ports (and optionally all ports),
identifies the owning process, and attempts a TLS handshake to retrieve certificate
details such as subject, issuer, and protocol version.

Requirements:
    - Python 3.6+
    - Windows (uses psutil for process/connection enumeration)
    - Install dependency: pip install psutil

Usage:
    python tls_scanner.py [--all-ports] [--timeout SECONDS] [--no-probe]

Run as Administrator for full process visibility.
"""

import argparse
import platform
import socket
import ssl
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional

# ssl.SSLCertVerificationError was added in Python 3.7. On Python 3.6
# (shipped with RHEL 8) it does not exist, so fall back to ssl.SSLError,
# of which it is a subclass. This keeps the except clause valid everywhere.
SSLCertVerificationError = getattr(ssl, "SSLCertVerificationError", ssl.SSLError)

try:
    import psutil
except ImportError:
    print(
        "psutil is required but could not be imported by this Python "
        "interpreter:\n"
        f"    {sys.executable}\n"
        "Install it for THIS interpreter, e.g.:\n"
        f"    {sys.executable} -m pip install psutil\n"
        "or install the system package (RHEL/Fedora):\n"
        "    sudo dnf install python3-psutil"
    )
    sys.exit(1)


# Common ports that typically carry TLS traffic
TLS_PORTS = {443, 465, 587, 636, 853, 989, 990, 993, 995, 5223, 8443, 8883}


@dataclass
class TLSConnection:
    """Represents a detected TLS connection with process and certificate info."""
    local_addr: str
    local_port: int
    remote_addr: str
    remote_port: int
    status: str
    pid: int
    process_name: str
    process_exe: str
    tls_version: Optional[str] = None
    cipher: Optional[str] = None
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None
    cert_not_after: Optional[str] = None
    probe_error: Optional[str] = None


def get_tls_connections(all_ports: bool = False) -> List[TLSConnection]:
    """
    Enumerate established TCP connections and filter to those on TLS ports.
    Maps each connection to its owning process.
    """
    connections: List[TLSConnection] = []

    for conn in psutil.net_connections(kind="tcp"):
        # Only look at established connections with a remote address
        if conn.status != "ESTABLISHED" or not conn.raddr:
            continue

        remote_port = conn.raddr.port

        # Filter by TLS ports unless scanning all
        if not all_ports and remote_port not in TLS_PORTS:
            continue

        pid = conn.pid or 0
        process_name = "<unknown>"
        process_exe = ""

        if pid:
            try:
                proc = psutil.Process(pid)
                process_name = proc.name()
                process_exe = proc.exe() or ""
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        connections.append(TLSConnection(
            local_addr=conn.laddr.ip,
            local_port=conn.laddr.port,
            remote_addr=conn.raddr.ip,
            remote_port=remote_port,
            status=conn.status,
            pid=pid,
            process_name=process_name,
            process_exe=process_exe,
        ))

    return connections


def probe_tls(connection: TLSConnection, timeout: float = 3.0) -> TLSConnection:
    """
    Attempt a TLS handshake to the remote endpoint to retrieve certificate
    and protocol information. This creates a NEW connection to the same
    remote host/port — it does not interfere with the existing session.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # We just want to see what's there

    try:
        with socket.create_connection(
            (connection.remote_addr, connection.remote_port), timeout=timeout
        ) as sock:
            # remote_addr is always an IP (psutil gives us no hostname).
            # Sending an IP as SNI triggers TLSV1_UNRECOGNIZED_NAME on many
            # servers, so omit SNI entirely.
            with ctx.wrap_socket(sock, server_hostname=None) as tls_sock:
                connection.tls_version = tls_sock.version()
                cipher_info = tls_sock.cipher()
                if cipher_info:
                    connection.cipher = cipher_info[0]

                cert = tls_sock.getpeercert(binary_form=False)
                if not cert:
                    # With CERT_NONE we may only get binary form
                    pass
                else:
                    subj = dict(x[0] for x in cert.get("subject", []))
                    connection.cert_subject = subj.get("commonName", str(subj))
                    issr = dict(x[0] for x in cert.get("issuer", []))
                    connection.cert_issuer = issr.get("organizationName", str(issr))
                    connection.cert_not_after = cert.get("notAfter")

                # If getpeercert returned nothing, try binary
                if not connection.cert_subject:
                    der = tls_sock.getpeercert(binary_form=True)
                    if der:
                        connection.cert_subject = f"(binary cert, {len(der)} bytes)"

    except ssl.SSLError as e:
        # On Python 3.7+ SSLCertVerificationError is a distinct subclass of
        # SSLError; on 3.6 it does not exist. Inspect the exception to report
        # certificate verification failures specifically where possible.
        if SSLCertVerificationError is not ssl.SSLError and isinstance(
            e, SSLCertVerificationError
        ):
            connection.probe_error = f"Certificate verification failed: {e}"
        else:
            # e.reason is frequently None; str(e) carries the full OpenSSL message.
            detail = e.reason or str(e) or "handshake failed"
            connection.probe_error = f"SSL error: {detail}"
    except socket.timeout:
        connection.probe_error = "Connection timed out"
    except OSError as e:
        connection.probe_error = f"Network error: {e}"
    except Exception as e:
        connection.probe_error = f"Error: {e}"

    return connection


def _is_connection_refused(connection: TLSConnection) -> bool:
    """
    True if the probe failed because the remote endpoint refused the
    connection (errno 111 / ECONNREFUSED). These are noise when scanning
    all ports, since many endpoints are not TLS servers.
    """
    err = connection.probe_error
    if not err:
        return False
    return "Errno 111" in err or "Connection refused" in err


def format_results(connections: List[TLSConnection], show_probe: bool) -> str:
    """Format the scan results into a readable table."""
    # Drop connections whose probe was refused — they clutter the output,
    # especially with --all-ports. Only filter when probe data is shown.
    if show_probe:
        connections = [c for c in connections if not _is_connection_refused(c)]

    if not connections:
        return "No TLS connections found."

    lines = []
    separator = "-" * 120

    lines.append(separator)
    lines.append(
        f"{'PID':<7} {'Process':<25} {'Remote Endpoint':<30} {'Local Port':<11} "
        f"{'TLS Ver':<10} {'Cipher':<30}"
    )
    lines.append(separator)

    for c in sorted(connections, key=lambda x: (x.process_name.lower(), x.remote_port)):
        remote = f"{c.remote_addr}:{c.remote_port}"
        tls_ver = c.tls_version or ""
        cipher = c.cipher or ""

        if not show_probe:
            tls_ver = ""
            cipher = ""

        lines.append(
            f"{c.pid:<7} {c.process_name:<25} {remote:<30} {c.local_port:<11} "
            f"{tls_ver:<10} {cipher:<30}"
        )

        if show_probe and c.cert_subject:
            lines.append(f"        Subject: {c.cert_subject}")
            if c.cert_issuer:
                lines.append(f"        Issuer:  {c.cert_issuer}")
            if c.cert_not_after:
                lines.append(f"        Expires: {c.cert_not_after}")

        if show_probe and c.probe_error:
            lines.append(f"        Probe:   {c.probe_error}")

        if c.process_exe:
            lines.append(f"        Path:    {c.process_exe}")

        lines.append("")

    lines.append(separator)
    lines.append(f"Total TLS connections: {len(connections)}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Scan active TLS sessions on Windows and show owning processes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python tls_scanner.py                  Scan common TLS ports with probing
              python tls_scanner.py --all-ports      Scan all established TCP connections
              python tls_scanner.py --no-probe       Skip TLS handshake probing
              python tls_scanner.py --timeout 5      Set probe timeout to 5 seconds
        """),
    )
    parser.add_argument(
        "--all-ports", action="store_true",
        help="Scan all established TCP connections, not just common TLS ports",
    )
    parser.add_argument(
        "--timeout", type=float, default=3.0,
        help="Timeout in seconds for TLS probe connections (default: 3)",
    )
    parser.add_argument(
        "--no-probe", action="store_true",
        help="Skip TLS handshake probing (just show connections and processes)",
    )
    parser.add_argument(
        "--workers", type=int, default=10,
        help="Number of parallel probe workers (default: 10)",
    )

    args = parser.parse_args()

    system = platform.system()
    print(f"TLS Session Scanner for {system}")
    print("=" * 40)
    print()

    priv_hint = ("Administrator" if system == "Windows" else "root (sudo)")

    if not all(hasattr(psutil, attr) for attr in ["net_connections", "Process"]):
        print("Error: psutil version too old. Please upgrade: pip install --upgrade psutil")
        sys.exit(1)

    print("[*] Enumerating TCP connections...")
    connections = get_tls_connections(all_ports=args.all_ports)

    if not connections:
        port_info = "all ports" if args.all_ports else "TLS ports"
        print(f"[!] No established connections found on {port_info}.")
        print(f"    Try running as {priv_hint} for full visibility.")
        sys.exit(0)

    print(f"[*] Found {len(connections)} connection(s) on {'all' if args.all_ports else 'TLS'} ports.")

    if not args.no_probe:
        print(f"[*] Probing TLS endpoints (timeout={args.timeout}s, workers={args.workers})...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(probe_tls, conn, args.timeout): conn
                for conn in connections
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                # Update in place — probe_tls mutates and returns the same object
                future.result()
                print(f"\r[*] Probed {completed}/{len(connections)}", end="", flush=True)
        print()

    print()
    print(format_results(connections, show_probe=not args.no_probe))


if __name__ == "__main__":
    main()
