from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
 
model = ChatOpenAI(
    model="gpt-3.5-turbo",
    openai_api_key="sk-xxxxxxxxxxxxxxxxxxx",
    openai_api_base="https://api.aigc369.com/v1",
)
 
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个擅长{ability}的助手"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)
 
chain = prompt | model
 
chain_with_history = RunnableWithMessageHistory(
    chain,
    # 使用redis存储聊天记录
    lambda session_id: RedisChatMessageHistory(
        session_id, url="redis://10.20.1.10:6379/3"
    ),
    input_messages_key="question",
    history_messages_key="history",
)
 
# 每次调用都会保存聊天记录，需要有对应的session_id
chain_with_history.invoke(
    {"ability": "物理", "question": "地球到月球的距离是多少？"},
    config={"configurable": {"session_id": "baily_question"}},
)
 
chain_with_history.invoke(
    {"ability": "物理", "question": "地球到太阳的距离是多少？"},
    config={"configurable": {"session_id": "baily_question"}},
)
 
chain_with_history.invoke(
    {"ability": "物理", "question": "地球到他俩之间谁更近"},
    config={"configurable": {"session_id": "baily_question"}},
)
 