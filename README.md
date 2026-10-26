# TLS Session Scanner for Windows

Scans active TLS connections on your Windows machine and shows which process owns each connection. Optionally probes the remote endpoint to retrieve TLS version, cipher suite, and certificate details.

## Requirements

- Python 3.6+
- Windows OS
- Administrator privileges recommended (for full process visibility)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic scan — shows TLS connections on common ports with certificate probing
python tls_scanner.py

# Scan ALL established TCP connections (not just TLS ports)
python tls_scanner.py --all-ports

# Skip the TLS probe (faster, just lists connections and processes)
python tls_scanner.py --no-probe

# Increase probe timeout (useful for slow endpoints)
python tls_scanner.py --timeout 5

# Increase parallelism for probing
python tls_scanner.py --workers 20
```

## What It Does

1. **Enumerates TCP connections** — Uses `psutil` to list all established TCP connections.
2. **Filters to TLS ports** — By default only looks at ports commonly used for TLS (443, 465, 587, 636, 853, 993, 995, 8443, etc.). Use `--all-ports` to scan everything.
3. **Maps to processes** — Resolves each connection's owning PID to a process name and executable path.
4. **Probes TLS** — Opens a new TLS handshake to the same remote host:port to discover the TLS version, cipher suite, and server certificate details.

## Example Output

```
PID     Process                   Remote Endpoint                Local Port  TLS Ver    Cipher
------------------------------------------------------------------------------------------------------------------------
14320   chrome.exe                142.250.80.46:443              52341       TLSv1.3    TLS_AES_256_GCM_SHA384
        Subject: *.google.com
        Issuer:  Google Trust Services LLC
        Expires: Aug 25 2025
        Path:    C:\Program Files\Google\Chrome\Application\chrome.exe

8812    ms-teams.exe              52.113.194.132:443             49822       TLSv1.2    ECDHE-RSA-AES256-GCM-SHA384
        Subject: *.teams.microsoft.com
        Issuer:  Microsoft Corporation
        Path:    C:\Program Files\Microsoft\Teams\ms-teams.exe
```

Another real example:

```
PS D:\Python-scripts\WiP\tls-scanner> py.exe .\tls_scanner.py
TLS Session Scanner for Windows
========================================

[*] Enumerating TCP connections...
[*] Found 9 connection(s) on TLS ports.
[*] Probing TLS endpoints (timeout=3.0s, workers=10)...
[*] Probed 9/9

------------------------------------------------------------------------------------------------------------------------
PID     Process                   Remote Endpoint                Local Port  TLS Ver    Cipher
------------------------------------------------------------------------------------------------------------------------
2804    Code.exe                  13.89.179.10:443               50311       TLSv1.3    TLS_AES_256_GCM_SHA384
        Subject: (binary cert, 2677 bytes)
        Path:    C:\Users\admin_gdhaese1\AppData\Local\Programs\Microsoft VS Code\Code.exe

2804    Code.exe                  150.171.109.100:443            50321       TLSv1.3    TLS_AES_256_GCM_SHA384
        Subject: (binary cert, 1727 bytes)
        Path:    C:\Users\admin_gdhaese1\AppData\Local\Programs\Microsoft VS Code\Code.exe

3540    coreServiceShell.exe      23.37.197.171:443              50342       TLSv1.3    TLS_AES_256_GCM_SHA384
        Subject: (binary cert, 1882 bytes)
        Path:    C:\Program Files\Trend Micro\AMSP\coreServiceShell.exe

3540    coreServiceShell.exe      23.37.197.171:443              50393       TLSv1.3    TLS_AES_256_GCM_SHA384
        Subject: (binary cert, 1882 bytes)
        Path:    C:\Program Files\Trend Micro\AMSP\coreServiceShell.exe

3540    coreServiceShell.exe      23.37.197.171:443              50145       TLSv1.3    TLS_AES_256_GCM_SHA384
        Subject: (binary cert, 1882 bytes)
        Path:    C:\Program Files\Trend Micro\AMSP\coreServiceShell.exe

5172    dsa.exe                   18.97.19.28:443                57993       TLSv1.3    TLS_AES_128_GCM_SHA256
        Subject: (binary cert, 1361 bytes)
        Path:    C:\Program Files\Trend Micro\Deep Security Agent\dsa.exe

5452    EndpointBasecamp.exe      3.69.141.146:443               61231       TLSv1.2    ECDHE-RSA-AES128-GCM-SHA256
        Subject: (binary cert, 1554 bytes)
        Path:    C:\Program Files (x86)\Trend Micro\Endpoint Basecamp\EndpointBasecamp.exe

6436    ir_agent.exe              193.149.136.16:443             50204
        Probe:   Network error: [Errno 2] No such file or directory
        Path:    C:\Program Files\Rapid7\Insight Agent\components\insight_agent\4.0.13.32\ir_agent.exe

3080    telegraf.exe              10.77.169.27:443               50118
        Probe:   SSL error: TLSV1_UNRECOGNIZED_NAME
        Path:    C:\telegraf\bin\telegraf.exe

------------------------------------------------------------------------------------------------------------------------
Total TLS connections: 9
```

## Notes

- The TLS probe creates a **new** connection to the remote server — it does not intercept or modify existing traffic.
- Running without Administrator privileges may hide connections owned by system processes.
- Some endpoints may refuse the probe connection (firewalls, rate limiting), which is reported as a probe error.

## PyInstaller (create an EXE file)

```
pip install pyinstaller
pyinstaller --onefile tls_scanner.py
```

This produces a single `tls_scanner.exe` that bundles Python and all dependencies. No Python installation needed on the target machine.

Useful flags:

```python
--onefile — single EXE (slower startup, easier to distribute)
--console — keep the console window (default for scripts)
--icon=app.ico — custom icon
--uac-admin — request admin elevation on launch (useful here since the scanner benefits from it)
```

*Recommendation*

PyInstaller is the path of least resistance for your Windows. It handles psutil (which has C extensions) without extra config. A quick build command:

```
pyinstaller --onefile --uac-admin --name tls-scanner tls_scanner.py

```

The resulting `tls-scanner.exe` can be copied to any Windows machine and run directly — no Python install required. The `--uac-admin` flag will prompt for elevation automatically, which is ideal since the scanner needs admin rights for full process visibility.

## RPM Package (Linux / RHEL 9)

Although the tool is primarily aimed at Windows, it also runs on Linux
(`psutil` enumerates connections there too). An RPM package is provided for
RHEL 9 and compatible distributions.

### Build the RPM

Requires the `rpm-build` package (and optionally `rpmlint`):

```bash
sudo dnf install -y rpm-build rpmlint
./packaging/build-rpm.sh
```

The script stages a source tarball, runs `rpmbuild -ba`, and (if `rpmlint`
is installed) lints the result. Artifacts are written under the rpmbuild
tree, typically:

```
~/rpmbuild/RPMS/noarch/tls-scanner-1.0.0-1.el9.noarch.rpm
~/rpmbuild/SRPMS/tls-scanner-1.0.0-1.el9.src.rpm
```

### Install

```bash
dnf install --nobest tls-scanner
```

This pulls in `python3` and `python3-psutil` automatically.

### Run

Once installed, the tool is available on `PATH` as `tls-scanner`:

```bash
tls-scanner --no-probe      # list connections and processes
tls-scanner --all-ports     # scan all established TCP connections
man tls-scanner             # view the manual page
```

Run with `sudo` for full visibility of connections owned by other users'
processes.

### Package layout

| Path | Contents |
| --- | --- |
| `/usr/bin/tls-scanner` | Launcher that invokes the script with `python3` |
| `/usr/libexec/tls-scanner/tls_scanner.py` | The application |
| `/usr/share/man/man1/tls-scanner.1.gz` | Man page |
| `/usr/share/doc/tls-scanner/README.md` | This document |
| `/usr/share/licenses/tls-scanner/LICENSE` | License |

The packaging sources live in `packaging/`:

- `packaging/tls-scanner.spec` — RPM spec file
- `packaging/tls-scanner.1` — man page
- `packaging/build-rpm.sh` — build helper

