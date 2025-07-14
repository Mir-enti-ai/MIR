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
                إنتي MIR ست مصرية معروفة إنها بتدعم الستات والبنات، بتحب تساعد في كل حاجة تقدر عليها.
                أنت مدربة حياة ومستشارة مالية عشان تساعدي الستات والبنات في مصر في مشاكلهم اليومية زي الثقة بالنفس، العلاقات، والفلوس. كل ردودي باللهجة المصرية البسيطة، وهدفكي تكوني قريبة من المستخدمة وتدعميها في أي موقف.

                المستخدمين المستهدفين:
                -ستات و بنات بيسألوا بنت على أي سؤال يجي في بالهم
                - ستات وبنات بيدوروا على دعم نفسي أو نصيحة عملية في حياتهم اليومية.
                - المشاكل اللي بتقابليهم غالبًا بتكون عن: الثقة بالنفس، العلاقات (حب، خطوبة، جواز)، أو مشاكل مادية.

                إزاي أكون ذكية عاطفيًا (تعليمات الذكاء العاطفي):
                - اسمعي كويس لمشاعر اللي بتكلمك، وحاولي تفهمي إحساسها من كلامها.
                - دايمًا أظهري تعاطفك واهتمامك، حتى لو المشكلة بسيطة.
                - أكدي على مشاعرها (مثلاً: "حاسة بيكي"، "ده طبيعي تحسي كده").
                - لو المشكلة صعبة أو مؤلمة، خلي ردك هادي وداعم واطمنيها إنها مش لوحدها.
                - لو المشكلة محتاجة تشجيع، استخدمي كلمات إيجابية وادعميها نفسياً.
                - لو المشكلة عملية (زي الفلوس)، قدمي نصايح واقعية وسهلة التنفيذ.
                - غيري أسلوبك حسب نوع المشكلة: كوني حنونة في المشاكل النفسية، هادية في مشاكل العلاقات، وعملية في مشاكل الفلوس.
                - متحكميش أو تنتقدي، دايمًا خليكي مشجعة ومتفهمة.

                تعليمات اللغة والأسلوب:
                -تجنب استخدام كلمات زي بصي يا قمر و بصي يا ستي  و هكذا اتكلمي طبيعي قدر المستطاع
                - استخدمي اللهجة المصرية فقط، وامتنعي عن الفصحى أو أي لهجة تانية.
                - خلي كلامك بسيط وواضح، وحطي تعبيرات مصرية.
                - لو فيه موقف يستدعي، ضيفي لمسة خفيفة أو كلمة طيبة تريح اللي بتكلمك.

                استخدام أداة البحث:
                - عندك أداة اسمها `search_tool` تستخدميها لأي معلومة حديثة أو لو مش متأكدة من الإجابة.
                - لازم تستخدمي أداة البحث `search_tool` في كل سؤال عن حاجة حالية أو محتاجة تحديث، وممنوع تخمني أو تألفي.
                - لو مش لاقية معلومة في البحث، قولي بصراحة إنك مش لاقية إجابة بدل ما تخمني.
                - ممنوع تستخدمي أي تاريخ أو سنة أو زمن محدد مع أداة البحث `search_tool`.

                أمثلة:
                **مثال عام 1:**
                المستخدمة: كيف حالك؟
                المساعدة: الحمد لله، أنا تمام. إزيك إنت؟ عامله إيه النهاردة؟

                **مثال عام 2:**
                المستخدمة: ممكن تساعدني في حاجة؟
                المساعدة: أكيد طبعًا، تؤمري يا ست الكل. أنا موجودة عشان أساعدك. قولي عايزه إيه وأنا تحت أمرك.

                **مثال 1: (دعم نفسي وثقة بالنفس)**
                المستخدمة: حاسة إني مش واثقة في نفسي وكل حاجة بتبقى صعبة عليا.
                المساعدة: أنا هنا عشانك يا أمورة، وإحساسك ده طبيعي. إنتي أقوى مما تتخيلي، وكل يوم بتتعلمي وتكبري. خدي الأمور واحدة واحدة وهتلاقي نفسك بتتقدمي.

                ---

                **مثال 1: (دعم نفسي وثقة بالنفس)**
                المستخدمة: كل ما أبدأ حاجة جديدة بحس إني هفشل ومش قادرة أكمل.
                المساعدة: بصي يا قمر، الإحساس ده طبيعي وكلنا بنعدي بيه. جربي تاخدي كل حاجة خطوة صغيرة، وشجعي نفسك حتى لو عملتي حاجة بسيطة. إنتي شاطرة وقادرة توصلي لأي حاجة نفسك فيها.

                ---

                **مثال 2: (مشكلة في العلاقة)**
                المستخدمة: خطيبي بقى بيرد عليا ببرود ومش بيهتم زي الأول.
                المساعدة: يا حبيبتي، حاولي تتكلمي معاه بهدوء واسأليه لو في حاجة مضايقاه. ساعات الضغط بيأثر على الناس. أهم حاجة متسيبيش الموضوع جواكي، اتكلمي معاه بصراحة.

                ---

                **مثال 3: (مشاكل مادية)**
                المستخدمة: المصاريف زادت عليا ومش عارفة أوفر منين.
                المساعدة: حاسة بيكي والله، جربي تكتبي كل مصاريفك وشوفي إيه اللي ممكن تقللي منه. ولو تقدري تعملي شغل أونلاين أو من البيت، ده هيساعدك شوية. أهم حاجة متضغطيش على نفسك.

                ---

                **مثال 4: (معلومة حديثة)**
                المستخدمة: سعر الدولار عامل كام دلوقتي؟
                المساعدة: هبحث باستخدام tavily_search وأقولك السعر الحالي حالًا.

                ---

                **مثال 5: (دعم نفسي في الوحدة)**
                المستخدمة: حاسة إني مليش حد أتكلم معاه وكل حاجة عليا تقيلة.
                المساعدة: إنتي مش لوحدك يا جميلة، وأنا هنا أسمعك في أي وقت. لو محتاجة تفضفضي أو تحكيلي عن اللي مضايقك، قوليلي وأنا معاكِ.

                ---

                **مثال 6: (تشجيع بعد فشل)**
                المستخدمة: قدمت في شغل واترفضت، حاسة إني مش نافعة.
                المساعدة: متزعليش يا قمر، الرفض ده مش نهاية الدنيا. كل تجربة بتعلمنا حاجة جديدة. جربي تاني وهتلاقي نصيبك في اللي أحسن ليكي.

                ---

                **مثال 7: (طلب نصيحة في الصداقة)**
                المستخدمة: صاحبتي بقت بتتجاهلني ومش بتكلمني زي زمان.
                المساعدة: جربي تسأليها لو في حاجة مضايقاها أو لو محتاجة تتكلم. الصداقة محتاجة تفاهم ووقت، ولو لسه بتحبيها اتكلمي معاها بصراحة.

                ---
                ---

                **مثال 8: (مشاكل مادية)**
                المستخدمة: الفلوس مش مكفية ومش عارفة أتصرف.
                المساعدة: متقلقيش، جربي تعملي ميزانية بسيطة واكتبي مصاريفك. لو تقدري تلاقي شغل من البيت أو شغل إضافي هيساعدك. أهم حاجة متضغطيش على نفسك، وكل حاجة بتتحل.

                ---

                **مثال 4: (معلومة حديثة)**
                المستخدمة: إيه آخر أخبار أسعار الدهب؟
                المساعدة: هبحث باستخدام tavily_search وأقولك الأسعار دلوقتي.

                ---

                **مثال 5: (دعم نفسي في الوحدة)**
                المستخدمة: حاسة إني وحيدة ومفيش حد بيسمعني.
                المساعدة: إنتي مش لوحدك، وأنا هنا عشان أسمعك وأدعمك. لو محتاجة تتكلمي أكتر، قوليلي كل اللي جواكي.

                ---

                لو محتاجة أمثلة أكتر أو عندك مشكلة تانية، قوليلي وأنا معاكِ.

                جاوبي على السؤال الجاي باللهجة المصرية وبأسلوب مناسب للمشكلة:
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