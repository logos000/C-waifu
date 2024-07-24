import operator
from datetime import datetime
from typing import Annotated, TypedDict, Union, Type

from dotenv import load_dotenv
from langchain import hub
from langchain.agents import create_react_agent, tool
from langchain_community.chat_models import ChatOllama
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.tools import BaseTool
from langgraph.prebuilt import ToolExecutor, ToolNode
from langchain.pydantic_v1 import BaseModel, Field
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolInvocation
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate,MessagesPlaceholder
from langchain_community.utilities import SerpAPIWrapper
import os

from langchain_community.document_loaders import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from langchain_community.vectorstores import chroma

# 定义获取当前时间的工具输入模型
class GetNowInput(BaseModel):
    format: str = Field(..., description="时间格式")

# 定义获取当前时间的工具
class GetNow(BaseTool):
    args_schema: Type[BaseModel] = GetNowInput
    description = "只有在需要获取当前时间时，才可以使用这个工具。若用户没输入时间格式，则需要输入'%Y-%m-%d %H:%M:%S'作为时间格式format"
    name = "get_now"

    async def _arun(self, format: str) -> str:
        print("异步调用了获取时间的方法")
        return datetime.now().strftime(format)

    def _run(self, format: str) -> str:
        print("调用了获取时间的方法")
        return datetime.now().strftime(format)

os.environ["SERPAPI_API_KEY"] = "66425169b4775085d7ff617e6d547119482ee279211864ea8a78fd57e61a7d10"

@tool("my_search_tool")
def search(query):
    """
    只有在需要获取实时信息或者不知道的信息的时候，才可以使用这个工具
    根据给定的查询执行搜索并返回结果。

    使用SerpAPIWrapper类来封装搜索操作，该类负责与外部API交互，
    提供了一个简洁的方法来获取搜索结果。

    参数:
    - query: 字符串，表示要搜索的查询关键词。

    返回:
    - result: 字典，包含搜索结果的详细信息，具体结构取决于SerpAPI的返回。
    """
    # 初始化SerpAPI的包装类，这个类负责实际的搜索操作。
    serp = SerpAPIWrapper()
    # 使用给定的查询执行搜索，并返回结果。
    result = serp.run(query)
    # 返回搜索结果。
    return result

@tool("rag_tool")
def rag_request(query):
    """
    需要获取历史消息记录的时候，才可以使用这个工具
    根据给定的查询执行搜索并返回结果。



    参数:
    - query: 字符串，表示要搜索的查询关键词。

    返回:
    - result: 字典，包含搜索结果的详细信息，具体结构取决于SerpAPI的返回。
    """
    loader = Docx2txtLoader("aa.docx")
    text = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300,chunk_overlap=50,length_function=len,add_start_index=True)

    embedding = OllamaEmbeddings(model="mxbai-embed-large")

    fs = LocalFileStore("../cache/")
    cache_embedding = CacheBackedEmbeddings.from_bytes_store(embedding,fs, namespace=embedding.model)
    print(list(fs.yield_keys()))
    data = text_splitter.split_text(text=text[0].page_content)
    #
    db = chroma.Chroma.from_texts(texts=data,embedding=cache_embedding)

    print(list(fs.yield_keys()))
    retriver = db.as_retriever()    

# 加载工具并设置代理
tools = [GetNow(),search]
tool_node = ToolNode(tools)
tool_executor = ToolExecutor(tools)

# 定义代理状态类型
class AgentState(TypedDict):
    input: HumanMessage
    chat_history: list[BaseMessage]
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]

# 初始化聊天模型
model = ChatOllama(model="cielo")

# 拉取 REACT 代理的提示模板
prompt = hub.pull("hwchase17/react")
#prompt = PromptTemplate.from_file('prompt_template.txt')
#print(prompt)
# 创建代理可运行对象
agent_runnable = create_react_agent(model, tools, prompt)

def execute_tools(state):
    print("Called `execute_tools`")
    last_message = state["agent_outcome"]

    tool_name = last_message.tool
    tool_input = last_message.tool_input

    print(f"Calling tool: {tool_name} with input: {tool_input}")

    action = ToolInvocation(
        tool=tool_name,
        tool_input=tool_input,
    )
    response = tool_executor.invoke(action)
    state["intermediate_steps"].append((last_message, response))
    return state

def run_agent(state):
    """
    这是调用大模型的方法
    :param state:
    :return:
    """
    agent_outcome = agent_runnable.invoke(state)
    state["agent_outcome"] = agent_outcome
    return state

def should_continue(state):
    last_message = state["agent_outcome"]
    if isinstance(last_message, AgentFinish):
        return "end"
    else:
        return "continue"

workflow = StateGraph(AgentState)

workflow.add_node("agent", run_agent)
workflow.add_node("action", execute_tools)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent", should_continue, {"continue": "action", "end": END}
)

workflow.add_edge("action", "agent")
app = workflow.compile()

messages = [
    SystemMessage(content="你是一个对话助手，请用可爱的语气说话，在每句话末尾加上喵"),
    HumanMessage(content="你好"),
    AIMessage(content="你好，请问有什么可以帮你")
]

while True:
    human = input("请输入你的问题：")
    state = {
        "input": [messages,HumanMessage(content=human)],
        "chat_history": None,
        "agent_outcome": None,
        "intermediate_steps": []
    }
    
    res = app.invoke(state, config={"configurable": {"tread_id": 1}})
    messages.append(HumanMessage(content=human))
    ai_response = res["agent_outcome"].return_values['output']
    messages.append(AIMessage(content=ai_response))
    
    print(res)
    print(ai_response)