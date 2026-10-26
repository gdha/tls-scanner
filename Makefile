NAME    := tls-scanner
VERSION := 1.0.0

.PHONY: all clean rpm exe help

all: help

help:
	@echo "Targets:"
	@echo "  clean  - remove build artifacts (caches, PyInstaller & RPM output)"
	@echo "  rpm    - build the RPM package (packaging/build-rpm.sh)"
	@echo "  exe    - build a standalone EXE via PyInstaller"

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
