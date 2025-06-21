from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

MODEL = "gpt-3.5-turbo"  # choose a low‑cost model for summarisation
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
summary_chain: Runnable = prompt | llm | StrOutputParser()


async def summarize(existing_summary: str, history_as_text: str) -> str:
    """Convenience wrapper that feeds the chain.

    Args:
        existing_summary: The previous running summary (may be empty).
        history_as_text:  The latest chat messages joined into a single string.

    Returns:
        The updated summary produced by the LLM.
    """
    return await summary_chain.ainvoke(
        {
            "existing_summary": [SystemMessage(content=existing_summary)] if existing_summary else [],
            "new_messages": [HumanMessage(content=history_as_text)],
        }
    )
