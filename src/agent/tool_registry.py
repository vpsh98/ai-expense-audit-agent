from typing import Any, Dict, List, Optional
from src.tools import (
    BaseTool,
    calculator_tool,
    get_employee_details_tool,
    read_expense_report_tool,
    search_expense_policy_tool,
    check_approval_tool,
    read_receipt_tool,
)
from src.models import ToolResult
from src.utils.logger import logger

class ToolRegistry:
    """Central registry to manage, format schemas, and execute agent tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance into the registry."""
        if not hasattr(tool, "name") or not tool.name:
            raise ValueError("Tool must have a non-empty 'name' attribute.")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: '{tool.name}'")

    def register_defaults(self) -> None:
        """Registers all core expense audit domain tools."""
        self.register(calculator_tool)
        self.register(get_employee_details_tool)
        self.register(read_expense_report_tool)
        self.register(search_expense_policy_tool)
        self.register(check_approval_tool)
        self.register(read_receipt_tool)

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Retrieves a tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """Returns names of all registered tools."""
        return list(self._tools.keys())

    def get_schemas(self, provider_format: str = "standard") -> List[Dict[str, Any]]:
        """Returns JSON Function Call schemas for registered tools.
        
        Supported provider formats:
          - 'standard' / 'gemini': [{"name": ..., "description": ..., "parameters": ...}]
          - 'openai': [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
        """
        schemas = []
        for name, tool in self._tools.items():
            base_schema = tool.to_json_schema()
            if provider_format.lower() == "openai":
                schemas.append({
                    "type": "function",
                    "function": base_schema
                })
            else:
                schemas.append(base_schema)
        return schemas

    def execute(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Safely dispatches tool call execution by tool name."""
        tool = self.get(tool_name)
        if not tool:
            err_msg = f"Tool '{tool_name}' is not registered in ToolRegistry. Available tools: {self.list_tools()}"
            logger.warning(err_msg)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=err_msg
            )

        args = arguments or {}
        return tool.run(**args)

    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Default singleton registry instance
default_registry = ToolRegistry()
default_registry.register_defaults()
