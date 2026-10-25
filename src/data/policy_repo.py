import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from src.config import settings
from src.utils.logger import logger

class PolicyRepository:
    """Repository for querying corporate expense spending policies."""

    def __init__(self, data_path: Optional[Union[str, Path]] = None):
        self.data_path = Path(data_path) if data_path else settings.DATA_DIR / "policies.json"
        self._policies: List[Dict[str, Any]] = []
        self.load_data()

    def load_data(self) -> None:
        """Loads policy rules from JSON file."""
        if not self.data_path.exists():
            logger.warning(f"Policy data file not found at {self.data_path}")
            self._policies = []
            return
        
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._policies = json.load(f)
            logger.info(f"Loaded {len(self._policies)} policy rules from {self.data_path}")
        except Exception as e:
            logger.error(f"Error loading policy data from {self.data_path}: {e}")
            self._policies = []

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all policy records."""
        return list(self._policies)

    def get_by_category(self, category: str) -> Optional[Dict[str, Any]]:
        """Finds policy rule by category name (case-insensitive with alias mapping)."""
        if not category:
            return None
        target_cat = category.strip().lower()

        # Direct exact match
        for pol in self._policies:
            if pol.get("category", "").strip().lower() == target_cat:
                return pol

        # Category alias mappings
        aliases = {
            "wfh": "wfh_setup",
            "wfh_setup": "wfh_setup",
            "wfh setup": "wfh_setup",
            "home office": "wfh_setup",
            "work from home": "wfh_setup",
            "wfh equipment": "wfh_setup",
            "course": "course",
            "courses": "course",
            "training": "course",
            "certification": "course",
            "software": "software_license",
            "software_license": "software_license",
            "software license": "software_license",
            "saas": "software_license",
            "travel": "travel",
            "trip": "travel",
        }
        if target_cat in aliases:
            mapped = aliases[target_cat]
            for pol in self._policies:
                if pol.get("category", "").strip().lower() == mapped:
                    return pol

        # Check if target_cat is an item in item_limits (e.g. 'monitor')
        for pol in self._policies:
            item_limits = pol.get("item_limits", {})
            if isinstance(item_limits, dict) and target_cat in [k.lower() for k in item_limits]:
                return pol

        return None

    def get_item_limit(self, category: str, item: str) -> Optional[float]:
        """Returns monetary spending limit for a specific item within a category (e.g. monitor)."""
        policy = self.get_by_category(category)
        if not policy or not item:
            return None
        item_limits = policy.get("item_limits", {})
        if isinstance(item_limits, dict):
            item_key = item.strip().lower()
            for k, v in item_limits.items():
                if k.lower() == item_key:
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return None
        return None

    def get_limit_for_category(self, category: str, item: Optional[str] = None) -> Optional[float]:
        """Returns monetary spending limit for a given category (or item within category)."""
        if item:
            item_limit = self.get_item_limit(category, item)
            if item_limit is not None:
                return item_limit

        policy = self.get_by_category(category)
        if policy and "limit_amount" in policy:
            try:
                return float(policy["limit_amount"])
            except (ValueError, TypeError):
                return None
        return None
