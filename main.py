from src.agent import app
from langchain_core.messages import HumanMessage

def run_agent():
    print("--- Local Agent Started (Type 'quit' to exit) ---")
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            break

        inputs = {"messages": [HumanMessage(content=user_input)]}
        
        for output in app.stream(inputs):
            for key, value in output.items():
                print(f"Agent: {value['messages'][-1].content}")

if __name__ == "__main__":
    print(app.get_graph().draw_ascii())