import operator
from datetime import datetime
from typing import Annotated, TypedDict, Union

from dotenv import load_dotenv
from langchain import hub
from langchain.agents import create_react_agent,create_openai_tools_agent
from langchain_community.chat_models import ChatOllama
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation

from langchain.tools import BaseTool
from langgraph.prebuilt import ToolNode
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai.chat_models import ChatOpenAI

#os.environ["OPENAI_API_BASE"] = "https://api.fe8.cn/v1"
#os.environ["OPENAI_API_KEY"] = "sk-nA4XFQzD7IZc8fVTcLDFqH1ds9ySyS39hpl46eOxiTltIfph"
class get_now_input(BaseModel):
    format: str = Field(..., description="时间格式")


class get_now(BaseTool):
    args_schema: Type[BaseModel] =get_now_input
    description = "这是一个获取当前时间的方法，若用户没输入时间格式，则使用'%Y-%m-%d %H:%M:%S'作为时间格式format"
    name = "get_now"

    async def _arun(self, format: str) -> str:
        print("异步调用了获取时间的方法")
        return datetime.now().strftime(format)

    def _run(self, format: str) -> str:
        print("调用了获取时间的方法")
        return datetime.now().strftime(format)


tools = [get_now()]
tool_node = ToolNode(tools)
tool_executor = ToolExecutor(tools)

class AgentState(TypedDict):
    input: str
    chat_history: list[BaseMessage]
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]

#model = ChatOpenAI(temperature=0,model="gpt-4o",api_key="sk-fVxALjqWNXclhzatHRgPdAiNeRHezeSBb4PcqQ9RPBARMOjW",base_url="https://api.fe8.cn/v1").bind_tools(tools)
model = ChatOllama(model="cielo")
prompt = hub.pull("hwchase17/react")


agent_runnable = create_react_agent(model, tools, prompt)
#agent_runnable.invoke({"input":HumanMessage(content="现在几点了")})
#agent_excuter = create_openai_tools_agent(model, tools, prompt)
#agent_excuter.invoke({"input":HumanMessage(content="现在几点了")})

def execute_tools(state):
    print("Called `execute_tools`")
    messages = [state["agent_outcome"]]
    last_message = messages[-1]

    tool_name = last_message.tool

    print(f"Calling tool: {tool_name}")

    action = ToolInvocation(
        tool=tool_name,
        tool_input=last_message.tool_input,
    )
    response = tool_executor.invoke(action)
    return {"intermediate_steps": [(state["agent_outcome"], response)]}


def run_agent(state):
    """
    这是调用大模型的方法
    :param state:
    :return:
    """
    agent_outcome = agent_runnable.invoke(state)
    return {"agent_outcome": agent_outcome}


def should_continue(state):
    messages = [state["agent_outcome"]]
    last_message = messages[-1]
    if "Action" not in last_message.log:
        return "end"
    else:
        return "continue"
    
workflow = StateGraph(AgentState)

workflow.add_node("agent", run_agent)
workflow.add_node("action", execute_tools)
#workflow.add_node("action",tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent", should_continue, {"continue": "action", "end": END}
)


workflow.add_edge("action", "agent")
app = workflow.compile()

messages = [SystemMessage(content="你是一个获取当前时间的助手"),
            HumanMessage(content="你好"),
            AIMessage(content="你好，请问有什么可以帮你")]


while True:
    human = input("请输入你的问题：")
    
    res = app.invoke({"input":human,"chat_history": messages},config={"configurable":{"tread_id":1}})
    messages.append(HumanMessage(content=human))
    messages.append(AIMessage(content=res["agent_outcome"].return_values['output']))
    print(res)