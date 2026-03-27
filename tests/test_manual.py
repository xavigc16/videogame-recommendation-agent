from src.agent import app
from langchain_core.messages import HumanMessage

def run_trace_test():
    inputs = {"messages": [HumanMessage(content="What is the capital of France?")]}
    
    for output in app.stream(inputs):
        for node_name, state in output.items():
            print(f"\nNode Executed: {node_name}")
            print(f"Memory (State): {state}")
            print("-" * 20)

if __name__ == "__main__":
    run_trace_test()