#!/usr/bin/env python3
"""Set only the local Control Center admin secret using hidden terminal input.

This tool does not accept supplier credentials and is not run during the MVP build.
"""
from __future__ import annotations

import getpass
import os
import sys
import tempfile
from pathlib import Path

CONFIG = Path(os.environ.get("KATE_CONFIG_FILE", str(Path.home() / ".config/kate-mvp/server.env"))).expanduser()


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: python3 tools/configure_server_secret.py", file=sys.stderr)
        return 2
    try:
        first = getpass.getpass("Enter Control Center admin secret (input hidden; saved outside the repository): ")
        if not first:
            print("No value saved.", file=sys.stderr)
            return 2
        second = getpass.getpass("Confirm admin secret (input hidden): ")
        if first != second:
            print("Values did not match; no value saved.", file=sys.stderr)
            return 2
        if len(first) < 24:
            print("Admin secret must be at least 24 characters; no value saved.", file=sys.stderr)
            return 2
        CONFIG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(CONFIG.parent, 0o700)
        if CONFIG.exists() and (CONFIG.is_symlink() or not CONFIG.is_file()):
            print("Config path is not a regular file; no value saved.", file=sys.stderr)
            return 2
        if CONFIG.exists() and (CONFIG.stat().st_mode & 0o077):
            print("Existing config file permissions are not private; no value saved.", file=sys.stderr)
            return 2
        fd, temp_name = tempfile.mkstemp(prefix=".server.env.", dir=str(CONFIG.parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(f"KATE_ADMIN_SECRET={first}\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, CONFIG)
            os.chmod(CONFIG, 0o600)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        print("Admin secret stored outside the repository with owner-only permissions. Restart the service to load it.")
        return 0
    except (OSError, UnicodeError, EOFError) as exc:
        print(f"Could not update private admin configuration ({type(exc).__name__}); no value was printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
