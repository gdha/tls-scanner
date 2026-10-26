NAME    := tls-scanner
VERSION := 1.0.0

.PHONY: all clean deb rpm exe help

all: help

help:
	@echo "Targets:"
	@echo "  clean  - remove build artifacts (caches, PyInstaller & package output)"
	@echo "  deb    - build the Debian package (packaging/build-deb.sh)"
	@echo "  rpm    - build the RPM package (packaging/build-rpm.sh)"
	@echo "  exe    - build a standalone EXE via PyInstaller"

# Build the Debian package.
deb:
	./packaging/build-deb.sh

# Build the RPM package.
rpm:
	./packaging/build-rpm.sh

# Build a standalone executable via PyInstaller.
exe:
	pyinstaller --onefile --uac-admin --name $(NAME) tls_scanner.py

# Remove generated build artifacts.
clean:
	rm -rf build/ dist/ __pycache__/
	rm -f *.spec.bak
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
