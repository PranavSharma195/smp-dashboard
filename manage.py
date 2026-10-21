#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Run `bash setup_mac.sh` (or setup_windows.bat) "
            "first so the project's virtual environment is created."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
