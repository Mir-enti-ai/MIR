import os
os.environ["OPENAI_API_KEY"]="sk-"
os.environ["TAVILY_API_KEY"]="tvly-"


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableLambda, ConfigurableFieldSpec
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain import hub
#from langchain_tavily import TavilySearch
from langchain_core.tools import tool

from tavily import TavilyClient

tavily_client = TavilyClient()


from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app= FastAPI(title="Langchain Chatbot")

chat_model= ChatOpenAI(model="gpt-4.1", temperature=0.0, streaming=True)
# tavily_search_tool= TavilySearch()
agent_prompt= hub.pull("hwchase17/openai-functions-agent")

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

@tool
def search_tool(query: str) -> str:
    """A search engine optimized for comprehensive, accurate, and trusted results. Useful for when you need to answer questions about current events. It not only retrieves URLs and snippets, but offers advanced search depths, domain management, time range filters, and image search, this tool delivers real-time, accurate, and citation-backed results. 
    Input should be a search query.
    query: target concise search query without any date
    """
    response = tavily_client.search(query)
    output = "\n\n".join(
        f"Title: {item['title']}\nContent: {item['content']}"
        for item in response['results']
    )
    return output

search_tool

agent_prompt.messages[0].prompt.template= system_prompt


openai_agent= create_openai_functions_agent(
    llm= chat_model,
    prompt= agent_prompt,
    tools= [search_tool]
)


agent_executor= AgentExecutor(
    agent= openai_agent,
    tools= [search_tool],
    handle_parsing_errors= True
)

store= {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id]= ChatMessageHistory()
    return store[session_id]

runnable_chain= RunnableWithMessageHistory(
    runnable= agent_executor,
    get_session_history= get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output",
    history_factory_config=[
        ConfigurableFieldSpec(
            id="session_id",
            name="session id",
            description="Unique Identifier",
            annotation= str,
            default="",
            is_shared= True
        )
    ]
)

@app.get("/")
def welcome():
    return {"message": "The web server is working fine."}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint to handle chat messages with streaming.
    """
    await websocket.accept()
    try:
        while True:
            received_message = await websocket.receive_text()
            print(f"Received message from {client_id}: {received_message}")
            
            # Use stream to get chunks of the response
            async for chunk in runnable_chain.astream(
                {"input": received_message},
                {"configurable": {"session_id": client_id}}
            ):
                response_content = ""
                if "output" in chunk:
                    response_content = chunk["output"]
                elif "content" in chunk:
                    response_content = chunk["content"]
                elif isinstance(chunk, str):
                    response_content = chunk
                
                if response_content:
                    print(f"Streaming chunk to {client_id}: {response_content}")
                    await websocket.send_text(response_content)

    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected.")
    except Exception as e:
        print(f"An error occurred for client {client_id}: {e}")
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass

