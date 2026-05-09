import sys

from src.agent import ask_agent


def main() -> None:
    query = " ".join(sys.argv[1:]) or "What do people generally think about Consume Me?"
    print(ask_agent(query))


if __name__ == "__main__":
    main()
