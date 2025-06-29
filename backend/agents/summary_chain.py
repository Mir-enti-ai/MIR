from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

MODEL = "gpt-4.1-2025-04-14" 
llm = ChatOpenAI(model_name=MODEL, temperature=0.2)

# Arabic system instruction
system_instruction = (
    "أنت مساعد دردشة يركّز على دعم النساء العربيات في مختلف الجوانب الشخصية "
    "والمهنية. مهمتك تلخيص المحادثة في ملخص موجز يحتفظ بأهم التفاصيل الشخصية، "
    "القرارات، والمهام المعلَّقة. لا تقم باختراع أي معلومات جديدة."
)

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=system_instruction),
        MessagesPlaceholder(variable_name="existing_summary", optional=True),
        SystemMessage(
            content=(
                "فيما يلي أحدث الرسائل التي يجب دمجها في الملخص. "
                "حدِّث الملخص بحيث يظل في حدود 150 كلمة تقريبًا."
            )
        ),
        MessagesPlaceholder(variable_name="new_messages"),
        HumanMessage(content="قدِّم الملخص المحدَّث فقط:\n<الملخص المحدث>"),
    ]
)

# Build the runnable: prompt → LLM → string output
summary_chain: Runnable = prompt | llm 

def extract_basic(ai_msg):
    """Return reply / token counts from an AIMessage."""
    reply = ai_msg.content

    # OpenAI v2 puts usage stats in response_metadata.token_usage
    usage = (
        getattr(ai_msg, "response_metadata", None) or {}
    ).get("token_usage", {})

    # OpenAI v1 style (usage_metadata) as fallback
    if not usage and getattr(ai_msg, "usage_metadata", None):
        usage = ai_msg.usage_metadata

    return {
        "reply":         reply,
        "input_tokens":  usage.get("prompt_tokens",  0),
        "output_tokens": usage.get("completion_tokens", 0),
    }

async def summarize(existing_summary: str, history_as_text: str) -> dict:
    """Convenience wrapper that feeds the chain.

    Args:
        existing_summary: The previous running summary (may be empty).
        history_as_text:  The latest chat messages joined into a single string.

    Returns:
        The updated summary produced by the LLM.
    """
    # Prepare the input for the summary chain
    response = await summary_chain.ainvoke(
        {
            "existing_summary": [SystemMessage(content=existing_summary)] if existing_summary else [],
            "new_messages": [HumanMessage(content=history_as_text)],
        }
    )

    # Extract the summary text from the response
    result= extract_basic(response)
    print(result)
    return result



