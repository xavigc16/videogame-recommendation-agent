from src.agent import agent
from langchain_core.messages import HumanMessage


def run_trace_test():
    inputs = {"messages": [HumanMessage(content="Recommend a relaxing farming game.")]}

    for output in agent.stream(inputs):
        for node_name, state in output.items():
            print(f"\nNode Executed: {node_name}")
            print(f"Memory (State): {state}")
            print("-" * 20)


if __name__ == "__main__":
    run_trace_test()
