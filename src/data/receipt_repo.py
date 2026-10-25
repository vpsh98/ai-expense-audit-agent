import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from src.config import settings
from src.utils.logger import logger

class ReceiptRepository:
    """Repository for loading and querying mock receipt metadata files."""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        self.data_dir = Path(data_dir) if data_dir else settings.DATA_DIR / "receipts"
        self._receipts: List[Dict[str, Any]] = []
        self.load_data()

    def load_data(self) -> None:
        """Loads receipt JSON files from the receipts directory."""
        if not self.data_dir.exists():
            logger.warning(f"Receipts directory not found at {self.data_dir}")
            self._receipts = []
            return

        try:
            receipts = []
            for file_path in self.data_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            receipts.append(data)
                        elif isinstance(data, list):
                            receipts.extend(data)
                except Exception as e:
                    logger.error(f"Error reading receipt file {file_path}: {e}")
            self._receipts = receipts
            logger.info(f"Loaded {len(self._receipts)} receipt records from {self.data_dir}")
        except Exception as e:
            logger.error(f"Error loading receipts from {self.data_dir}: {e}")
            self._receipts = []

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all loaded receipt records."""
        return list(self._receipts)

    def get_by_id(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Finds receipt by receipt ID (case-insensitive)."""
        if not receipt_id:
            return None
        target_id = receipt_id.strip().upper()
        for rcp in self._receipts:
            if rcp.get("receipt_id", "").strip().upper() == target_id:
                return rcp
        return None

    def get_by_expense_id(self, expense_id: str) -> Optional[Dict[str, Any]]:
        """Finds receipt linked to an expense ID (case-insensitive)."""
        if not expense_id:
            return None
        target_id = expense_id.strip().upper()
        for rcp in self._receipts:
            if rcp.get("expense_id", "").strip().upper() == target_id:
                return rcp
        return None

    def get_by_path(self, receipt_path: str) -> Optional[Dict[str, Any]]:
        """Finds receipt by relative or absolute receipt file path."""
        if not receipt_path:
            return None
        target_path = str(receipt_path).strip().lower().replace("\\", "/")
        for rcp in self._receipts:
            curr_path = str(rcp.get("receipt_path", "")).strip().lower().replace("\\", "/")
            if curr_path == target_path or curr_path.endswith(target_path) or target_path.endswith(curr_path):
                return rcp
        return None
