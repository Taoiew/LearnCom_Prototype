"""Load data from local files into the system."""

from pathlib import Path


class DataLoader:
    """Simple file-based data loader."""

    def load_text(self, file_path: str) -> str:
        path = Path(file_path)
        return path.read_text(encoding="utf-8") if path.exists() else ""
