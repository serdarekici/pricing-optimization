from __future__ import annotations

from pathlib import Path


def main() -> None:
    """Rebuild demo data (optional).

    This project already includes safe sample data under data/sample/.
    Keep real extracts under data/raw/ or data/private/ (git-ignored).
    """
    root = Path(__file__).resolve().parents[1]
    print(f"Sample data location: {root / 'data' / 'sample'}")


if __name__ == "__main__":
    main()
