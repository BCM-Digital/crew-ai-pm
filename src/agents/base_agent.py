"""Base Agent class for PM Agent system without CrewAI dependency."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import openai
from ..config import settings
from ..memory import memory
from ..tools.registry import get_default_tools, tool_by_name


class BaseAgent:
    """Base class for all PM agents."""
    
    def __init__(self, role: str, goal: str, backstory: str, tools: List = None):
        """Initialize the agent."""
        self.role = role
        self.goal = goal
        self.backstory = backstory
        # Merge built-in tools with provided list
        default_tools = get_default_tools()
        self.tools = tools or []
        # Ensure tools are unique by name
        existing_names = {getattr(t, 'name', t.__name__) for t in self.tools}
        for t in default_tools:
            if t.name not in existing_names:
                self.tools.append(t)
        if settings.openai_base_url:
            self.openai_client = openai.OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        else:
            self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def get_system_prompt(self) -> str:
        """Generate system prompt for the agent."""
        tools_description = ""
        if self.tools:
            tools_description = "\nAvailable tools (call by writing Tool:<name> JSON): " + \
                ", ".join([getattr(tool, 'name', tool.__name__) for tool in self.tools])
        
        return f"""You are a {self.role}.

Goal: {self.goal}

Background: {self.backstory}

{tools_description}

You can recall long-term memory relevant to the current task. Before answering, request memory search by writing: MemorySearch: <query>
To use a tool, write: Tool:<name> <json-args>. I will execute it and return results for you to continue.
"""
    
    def _build_messages(self, task_description: str, context: Dict[str, Any] | None) -> List[Dict[str, str]]:
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": task_description}
        ]
        if context:
            context_str = f"Additional context: {context}"
            messages.append({"role": "user", "content": context_str})
        return messages

    async def execute_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a task using OpenAI and available tools."""
        try:
            # Initial memory search prompt
            memory_hits = memory.query(task_description, top_k=5)
            memory_block = "\n\nRelevant memory:\n" + "\n".join([f"- {m.text}" for m in memory_hits]) if memory_hits else ""

            # Prepare the conversation
            messages = self._build_messages(task_description + memory_block, context)
            
            # Call OpenAI
            response = self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Execute tool calls iteratively if the assistant requests them
            tool_trace = []
            for _ in range(3):  # up to 3 tool interactions
                call = await self._detect_and_execute_tool(ai_response)
                if not call:
                    break
                tool_name, args, tool_result = call
                tool_trace.append({"tool": tool_name, "args": args, "result": tool_result})
                messages.append({"role": "assistant", "content": ai_response})
                messages.append({"role": "user", "content": f"ToolResult:{tool_name} {tool_result}"})
                response = self.openai_client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    max_tokens=1500,
                    temperature=0.7
                )
                ai_response = response.choices[0].message.content

            # Store brief summary to memory
            memory.add(
                text=f"[{self.role}] Task: {task_description[:140]} | Summary: {ai_response[:400]}",
                metadata={"agent": self.role, "created_at": datetime.now().isoformat()}
            )
            
            return {
                "success": True,
                "agent": self.role,
                "response": ai_response,
                "tool_trace": tool_trace,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "agent": self.role,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _detect_and_execute_tool(self, ai_response: str) -> Optional[tuple[str, Dict[str, Any], Any]]:
        lower = ai_response.strip()
        if lower.startswith("Tool:"):
            try:
                after = lower[len("Tool:"):].strip()
                # Split name and JSON args
                name, json_part = after.split(" ", 1)
                import json as _json
                args = _json.loads(json_part)
                tool = tool_by_name(name)
                if not tool:
                    return None
                result = tool.handler(args)
                return name, args, result
            except Exception:
                return None
        return None
    
    async def _execute_tool_calls(self, ai_response: str) -> List[Dict[str, Any]]:
        """Deprecated; retained for compatibility."""
        return [] 