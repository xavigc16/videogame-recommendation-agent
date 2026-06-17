from src.agent import agent
from langchain_core.messages import HumanMessage


def run_agent():
    print("--- Video Game Recommendation Agent (Type 'quit' to exit) ---")
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        inputs = {"messages": [HumanMessage(content=user_input)]}

        for output in agent.stream(inputs):
            for key, value in output.items():
                print(f"Agent: {value['messages'][-1].content}")


if __name__ == "__main__":
    run_agent()
