from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError
from src.models.agent import ToolResult
from src.utils.logger import logger

class BaseTool(ABC):
    """Abstract Base Class for all agent tools."""

    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = None

    def run(self, **kwargs) -> ToolResult:
        """Executes the tool with parameter validation and exception handling."""
        logger.debug(f"Executing tool '{self.name}' with args: {kwargs}")

        # Validate arguments using args_schema if available
        validated_args = kwargs
        if self.args_schema:
            try:
                # Support both unpacked kwargs or single dict argument
                if len(kwargs) == 1 and isinstance(next(iter(kwargs.values())), dict):
                    validated = self.args_schema.model_validate(next(iter(kwargs.values())))
                else:
                    validated = self.args_schema.model_validate(kwargs)
                validated_args = validated.model_dump()
            except ValidationError as ve:
                logger.error(f"Validation error in tool '{self.name}': {ve}")
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=f"Invalid arguments for tool '{self.name}': {ve}"
                )

        try:
            raw_output = self._run(**validated_args)

            # If tool already returned a ToolResult, return it directly
            if isinstance(raw_output, ToolResult):
                return raw_output

            # If raw output is dict with formatted_result, extract it
            formatted_res = None
            if isinstance(raw_output, dict) and "formatted_result" in raw_output:
                formatted_res = str(raw_output["formatted_result"])

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=raw_output,
                formatted_result=formatted_res or (str(raw_output) if raw_output is not None else None)
            )
        except Exception as e:
            logger.error(f"Error executing tool '{self.name}': {e}", exc_info=True)
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Execution error in tool '{self.name}': {str(e)}"
            )

    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """Internal execution logic implemented by specific tool."""
        pass

    def to_json_schema(self) -> Dict[str, Any]:
        """Generates JSON schema definition for LLM tool binding."""
        schema = {
            "name": self.name,
            "description": self.description,
            "parameters": {}
        }
        if self.args_schema:
            schema["parameters"] = self.args_schema.model_json_schema()
        return schema
