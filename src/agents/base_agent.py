"""Base Agent class for PM Agent system without CrewAI dependency."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import openai
from ..config import settings


class BaseAgent:
    """Base class for all PM agents."""
    
    def __init__(self, role: str, goal: str, backstory: str, tools: List = None):
        """Initialize the agent."""
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """Generate system prompt for the agent."""
        tools_description = ""
        if self.tools:
            tools_description = f"\nAvailable tools: {', '.join([tool.__name__ for tool in self.tools])}"
        
        return f"""You are a {self.role}.

Goal: {self.goal}

Background: {self.backstory}

{tools_description}

You should analyze the task, use available tools when appropriate, and provide clear, actionable results.
When using tools, format your response to indicate which tool you're calling and with what parameters.
"""
    
    async def execute_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a task using OpenAI and available tools."""
        try:
            # Prepare the conversation
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": task_description}
            ]
            
            # Add context if provided
            if context:
                context_str = f"Additional context: {context}"
                messages.append({"role": "user", "content": context_str})
            
            # Call OpenAI
            response = self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Execute any tool calls mentioned in the response
            tool_results = await self._execute_tool_calls(ai_response)
            
            return {
                "success": True,
                "agent": self.role,
                "response": ai_response,
                "tool_results": tool_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "agent": self.role,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_tool_calls(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response for tool calls and execute them."""
        tool_results = []
        
        # Simple tool call detection (you could make this more sophisticated)
        for tool in self.tools:
            tool_name = getattr(tool, 'name', tool.__name__)
            if tool_name.lower() in ai_response.lower():
                try:
                    # For now, we'll just indicate that tools would be called
                    # In a real implementation, you'd parse parameters and call the tool
                    tool_results.append({
                        "tool": tool_name,
                        "status": "would_execute",
                        "note": "Tool execution simulated - implement parameter parsing for real execution"
                    })
                except Exception as e:
                    tool_results.append({
                        "tool": tool_name,
                        "status": "error",
                        "error": str(e)
                    })
        
        return tool_results 