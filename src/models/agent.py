from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    """Standard container for tool execution outcomes."""
    tool_name: str = Field(..., description="Name of tool invoked")
    success: bool = Field(True, description="Whether execution succeeded")
    result: Any = Field(None, description="Output payload from tool")
    formatted_result: Optional[str] = Field(None, description="Formatted string representation of result")
    error: Optional[str] = Field(None, description="Error message if execution failed")


class AgentStep(BaseModel):
    """Container for single ReAct step within agent execution loop."""
    step_number: int = Field(..., description="1-indexed execution step counter")
    thought: str = Field(..., description="Reasoning/thought process of agent at step")
    action: Optional[str] = Field(None, description="Tool name invoked by agent")
    action_input: Optional[Dict[str, Any]] = Field(None, description="Arguments passed to tool")
    observation: Optional[Union[str, Dict[str, Any], ToolResult]] = Field(
        None, description="Output returned from tool execution"
    )
