import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_openai import ChatOpenAI
from functools import lru_cache
from typing import Annotated , Literal, Optional
from pydantic import Field 
from langchain_core.tools import tool
from textwrap import shorten


os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "").strip()
system_prompt = """

You are a life coach and financial advisor dedicated to supporting women and girls in Egypt. Your role is to help them navigate everyday challenges related to:

* Self-confidence and emotional resilience
* Relationships (dating, engagement, marriage, friendships)
* Personal finance (budgeting, saving, earning)
* Current, real-world data (e.g., currency exchange, gold prices, job opportunities, local services)

**Language & Tone Guidelines:**

* Always reply in simple, conversational **Egyptian Arabic**.
* Your tone should be **warm, respectful, and practical**,  encouraging without being sentimental, clingy, or overly emotional.
* Be emotionally intelligent: **listen carefully**, acknowledge the user's feelings calmly, and give **realistic, context-aware advice**.
* Ask follow-up questions when needed to understand the situation better before giving advice.

**Expected Topics & Questions:**

* Building self-confidence, managing emotions
* Relationship guidance (dating, breakups, marriage, friendships)
* Budgeting, saving, or increasing income
* Questions about current data (e.g., exchange rates, gold prices, job listings)
* Local recommendations (e.g., best places to eat koshary or get coffee in a specific area)

**Tool Use – `search_tool`:**

* Use `search_tool` for any **recent or changeable** information (e.g., prices, current events, job postings, or local services).
* Always use `search_tool` for local recommendations like restaurants or service providers.
* **Never guess**. If reliable information isn't available, say so clearly.
* After using `search_tool`, summarize results in Egyptian Arabic and give a **direct**, helpful response.

**Final Rule:**

* Always reply **entirely in Egyptian Arabic**, applying all instructions and using `search_tool` when up-to-date info is needed.


"""
_sys_msg = SystemMessage(content=system_prompt)


# ---------------------------------------------------------------------------
# 1.  State model
# ---------------------------------------------------------------------------
class State(MessagesState):
    """Session-level state carried through the LangGraph run."""
    called_tool_names: Annotated[
        list[str],
        Field(default_factory=list, json_schema_extra={"operation": "add"})
    ]
    total_input_tokens:  int = 0
    total_output_tokens: int = 0


# ---------------------------------------------------------------------------
# 2.  Graph factory
# ---------------------------------------------------------------------------
def _shared_graph() :
    """
    Build (or return if cached) the LangGraph that powers the agent.
    """
    # ---------- tools ----------


    @tool("tavily_search_results_json")
    async def tavily_pretty(query: str) -> str:
        """
        Search Tavily and return the top 3 results as a readable string.
        """
        tavily = TavilySearchResults(k=3)
        hits   = await tavily.ainvoke({"query": query})

        if not isinstance(hits, list):
            import json
            return json.dumps(hits, ensure_ascii=False)

        lines = []
        for idx, hit in enumerate(hits, start=1):
            title   = hit.get("title", "").strip() or "<no title>"
            url     = hit.get("url", "").strip()
            snippet = shorten(hit.get("content", ""), width=1000, placeholder="…")
            lines.append(f"{idx}. {title}\n   {url}\n   {snippet}")

        return "\n\n".join(lines)
    

    tools         = [tavily_pretty]
    tools_by_name = {tool.name: tool for tool in tools}

    # ---------- LLM ----------
    llm       = ChatOpenAI(model="gpt-4.1-2025-04-14", temperature=0.0)
    llm_tools = llm.bind_tools(tools, parallel_tool_calls=False)


    # ---------- NODE: assistant ----------
    async def assistant(state: State):
        """
            Run the LLM and accumulate token usage.

            Works with the OpenAI response structure you pasted, which looks like:
                content='…'
                additional_kwargs={…}
                response_metadata={
                    "token_usage": {
                        "prompt_tokens":      …,
                        "completion_tokens":  …,
                        …
                    },
                    …
                }
                usage_metadata={
                    "input_tokens":  …,
                    "output_tokens": …,
                    …
                }
        """
        model_response = await llm_tools.ainvoke([_sys_msg] + state["messages"])

        # ------------------------------------------------------------------
        # 1) Try the field you actually have: response_metadata.token_usage
        # ------------------------------------------------------------------
        in_tokens  = 0
        out_tokens = 0

        resp_meta = getattr(model_response, "response_metadata", None)
        if resp_meta and isinstance(resp_meta, dict):
            token_usage = resp_meta.get("token_usage", {})
            in_tokens   = token_usage.get("prompt_tokens",     0)
            out_tokens  = token_usage.get("completion_tokens", 0)


        # ------------------------------------------------------------------
        # 2) Fallback: usage_metadata 
        # ------------------------------------------------------------------
        if in_tokens == 0 and out_tokens == 0:
            usage_md = getattr(model_response, "usage_metadata", None)
            if usage_md and isinstance(usage_md, dict):
                in_tokens  = usage_md.get("input_tokens",  0)
                out_tokens = usage_md.get("output_tokens", 0)

        # ------------------------------------------------------------------
        # 3) Final fallback: LC/OpenAI .usage field (older LC versions)
        # ------------------------------------------------------------------
        if in_tokens == 0 and out_tokens == 0:
            usage = getattr(model_response, "usage", None) or {}
            in_tokens  = usage.get("prompt_tokens",     0)
            out_tokens = usage.get("completion_tokens", 0)

        return {
            "messages":            [model_response],
            "total_input_tokens":   state["total_input_tokens"] + in_tokens,
            "total_output_tokens":  state["total_output_tokens"] + out_tokens,
    }
    # ---------- NODE: tool_handler ----------
    async def tool_handler(state: State):
        """
        Execute the tool calls contained in the **last** assistant message and
        return a list of tool-role messages ready to be appended.
        """
        last_msg = state["messages"][-1]
        results  = []
        names    = []

        for tool_call in getattr(last_msg, "tool_calls", []):
            tool      = tools_by_name[tool_call["name"]]
            names.append(tool_call["name"])

            observation = await tool.ainvoke(tool_call["args"])
            results.append(
                {
                    "role":          "tool",
                    "content":       observation,
                    "tool_call_id":  tool_call["id"],
                }
            )

        return {
            "messages":           results,
            "called_tool_names":  names,           
        }

    # ---------- EDGE DECIDER ----------
    def should_continue(state: State) -> Literal["tool_handler", "__end__"]:
        """
        If the last assistant message contains tool calls *other than* Done,
        route to tool handler; otherwise stop.
        """
        last_msg = state["messages"][-1]
         # a) assistant made NO tool calls  → stop
        tool_calls = getattr(last_msg, "tool_calls", None)

        # a) assistant made NO tool calls  → stop
        if not tool_calls:
            return "__end__"

        # c) otherwise we still have real tool calls to run
        return "tool_handler"

    # ---------- BUILD GRAPH ----------
    builder = StateGraph(State)
    builder.add_node("assistant",     assistant)
    builder.add_node("tool_handler",  tool_handler)

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        should_continue,
        {
            "tool_handler": "tool_handler",
            "__end__":      END,
        },
    )
    builder.add_edge("tool_handler", "assistant")

    return builder.compile()

class MirAgent:
    def __init__(self):
        # Set API keys
        self.react_graph = _shared_graph()

    async def ask(self, messages: str) -> dict:
        result = await self.react_graph.ainvoke(
            {
            "messages": messages,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "called_tool_names": [],
        },
        
        )
        
        # Find the last AIMessage in the result
        ai_message = None
        for msg in reversed(result.get("messages", [])):
            if msg.__class__.__name__ == "AIMessage":
                ai_message = msg
                break
        reply = ai_message.content if ai_message else None

        return {
            "reply": reply,
            "output_tokens": result.get("total_output_tokens", 0),
            "input_tokens": result.get("total_input_tokens", 0),
            "tools": result.get("called_tool_names", []),
        }






# # test
# import asyncio

# agent = MirAgent()

# async def main():
#     while True:
#         user_input = input("Enter your question: ")
#         if user_input.lower() == "xxx":
#             break
#         response = await agent.ask(user_input)
#         print("Response:", response)

# if __name__ == "__main__":
#     asyncio.run(main())
# https://mir2-8slj.onrender.com/webhook