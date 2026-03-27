from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from src.llm import get_llm


class AgentState(TypedDict):
    messages: Annotated[List, "The conversation history"]

def call_model(state: AgentState):
    llm = get_llm()
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

#TODO: add some more nodes and a router to decide if RAG is neccessary

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)

workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()