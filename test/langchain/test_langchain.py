from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_community.vectorstores import DocArrayInMemorySearch




output_parser = StrOutputParser()
llm = Ollama(base_url='http://localhost:11434', model="cielo")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are world class technical documentation writer."),
    ("user", "{input}")
    ])

chain = prompt | llm | output_parser


for chunk in chain.stream({"input": "how can langsmith help with testing?"}):
    print(chunk, end="", flush=True)
#print(chain.invoke({"input": "how can langsmith help with testing?"}))