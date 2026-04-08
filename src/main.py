import os

from dotenv import load_dotenv
from typing import Annotated
from sentence_transformers import SentenceTransformer
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_postgres.vectorstores import PGVector
from langchain.tools.retriever import create_retriever_tool
from langchain_core.messages import BaseMessage

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


load_dotenv()

CONNECTION_STRING = f"postgresql+psycopg://{os.getenv('POSTGRE_USER')}:{os.getenv('POSTGRE_PASSWORD')}@{os.getenv('POSTGRE_HOST')}:{os.getenv('POSTGRE_PORT')}/{os.getenv('POSTGRE_DB')}"
COLLECTION_NAME = "video_game_reviews"

embeddings = SentenceTransformer("all-MiniLM-L6-v2")

vectorstore = PGVector(
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    connection=CONNECTION_STRING,
    use_jsonb=True, 
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
game_review_tool = create_retriever_tool(
    retriever,
    name="search_game_reviews",
    description="Searches and returns reviews, ratings, and community opinions about specific video games."
)

tools = [game_review_tool]

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

def call_model(state: AgentState):
    """Calls the LLM to decide what to do next."""
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def workflow_generation() -> StateGraph[AgentState]:
    """
    This function generates the workflow graph.
    We separate it out for clarity and potential reuse.
    """
    tool_node = ToolNode(tools)

    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition).
    workflow.add_edge("tools", "agent")

    return workflow.compile()

def ask_agent(query: str):
    print(f"User: {query}\n")
    
    app = workflow_generation()
    response_state = app.invoke({"messages": [("user", query)]})
    
    final_message = response_state["messages"][-1].content
    print(f"Agent:\n{final_message}\n")
    print("-" * 50)

if __name__ == "__main__":
    ask_agent("What do people generally think about Cyberpunk 2077?")