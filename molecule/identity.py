"""Resolve a checkout-local identity without publishing partial or competing IDs."""

import os
from pathlib import Path
import re
import sys
import tempfile
import uuid


def main():
    path = Path(sys.argv[1]) / ".molecule-id"
    if not path.exists():
        # A hard link publishes the complete file atomically and never replaces
        # an ID another Molecule process has already published.
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, prefix=".molecule-id-", delete=False
        ) as temporary:
            temporary.write(uuid.uuid4().hex + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(temporary.name, path)
        except FileExistsError:
            pass
        finally:
            Path(temporary.name).unlink()

    identity = path.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{32}", identity):
        sys.exit(f"Invalid test identity in {path}; recover the original ID before cleanup.")
    print(identity)


if __name__ == "__main__":
    main()
