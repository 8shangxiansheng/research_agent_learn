"""
LangChain Agent for Academic Q&A.
Provides streaming response with DeepSeek LLM and arxiv tool integration.
"""
import os
from typing import AsyncGenerator, List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.services.tools import arxiv_search


# System prompt for academic Q&A agent
SYSTEM_PROMPT = """You are an academic research assistant specialized in helping users understand and explore academic papers.

Your capabilities:
1. Search for academic papers on arXiv using the arxiv_search tool
2. Answer questions about research methodologies, paper summaries, and academic concepts
3. Help users find relevant papers for their research topics
4. Provide clear explanations of complex academic concepts

When responding:
- Be precise and cite sources when discussing papers
- Break down complex concepts into understandable parts
- Suggest related papers or topics when relevant
- If you need to search for papers, use the arxiv_search tool

Always be helpful, accurate, and thorough in your responses."""


class AcademicAgent:
    """
    Academic Q&A Agent with LangChain and DeepSeek integration.
    Supports streaming responses for real-time display.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        """
        Initialize the academic agent.

        Args:
            api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
            model: Model name (default: deepseek-chat)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable.")

        self.model = model

        # Initialize LLM with DeepSeek configuration
        self.llm = ChatOpenAI(
            model=self.model,
            openai_api_key=self.api_key,
            openai_api_base="https://api.deepseek.com/v1",
            temperature=0.7,
            streaming=True,
        )

        # Create react agent with tools
        self.agent = self._create_agent()

    def _create_agent(self):
        """Create the ReAct agent with arxiv search tool."""
        tools = [arxiv_search]

        # Create agent with system prompt
        agent = create_react_agent(
            self.llm,
            tools,
            prompt=SYSTEM_PROMPT
        )

        return agent

    def _format_history(self, history: List[Dict[str, str]]) -> List[BaseMessage]:
        """
        Format conversation history for LangChain.

        Args:
            history: List of message dicts with 'role' and 'content'

        Returns:
            List of LangChain message objects
        """
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return messages

    async def astream(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response for a query.

        Args:
            query: User query
            history: Optional conversation history

        Yields:
            Response chunks for real-time display
        """
        # Format messages
        messages = []
        if history:
            messages.extend(self._format_history(history))

        # Add current query
        messages.append(HumanMessage(content=query))

        # Stream response from agent
        async for event in self.agent.astream({"messages": messages}):
            # Handle different event types
            if "agent" in event:
                # Agent action
                if "messages" in event["agent"]:
                    for msg in event["agent"]["messages"]:
                        if hasattr(msg, "content") and msg.content:
                            yield msg.content
            elif "tools" in event:
                # Tool execution
                if "messages" in event["tools"]:
                    for msg in event["tools"]["messages"]:
                        if hasattr(msg, "content") and msg.content:
                            # Optionally yield tool results
                            pass

    async def ainvoke(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Get complete response for a query (non-streaming).

        Args:
            query: User query
            history: Optional conversation history

        Returns:
            Complete response string
        """
        # Format messages
        messages = []
        if history:
            messages.extend(self._format_history(history))

        # Add current query
        messages.append(HumanMessage(content=query))

        # Invoke agent
        result = await self.agent.ainvoke({"messages": messages})

        # Extract response
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content

        return ""

    def invoke(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Synchronous invoke for a query.

        Args:
            query: User query
            history: Optional conversation history

        Returns:
            Complete response string
        """
        import asyncio
        return asyncio.run(self.ainvoke(query, history))


# Singleton instance
_agent_instance: Optional[AcademicAgent] = None


def get_agent() -> AcademicAgent:
    """
    Get or create the agent singleton.

    Returns:
        AcademicAgent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AcademicAgent()
    return _agent_instance
