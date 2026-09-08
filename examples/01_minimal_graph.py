"""Lekcja 2: najmniejszy jawny graf. Uruchom: uv run python examples/01_minimal_graph.py"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    name: str
    result: str


def greet(state: State) -> dict[str, str]:
    return {"result": f"Cześć, {state['name']}!"}


builder = StateGraph(State)
builder.add_node("greet", greet)
builder.add_edge(START, "greet")
builder.add_edge("greet", END)
graph = builder.compile()

if __name__ == "__main__":
    print(graph.invoke({"name": "Ala", "result": ""}))
