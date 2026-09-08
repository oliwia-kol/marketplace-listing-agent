"""Lekcja 3: pauza i wznowienie. Uruchom: uv run python examples/02_interrupt.py"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    proposed_price: float
    approved_price: float


def approve_price(state: State) -> dict[str, float]:
    answer = interrupt({"question": "Cena?", "proposal": state["proposed_price"]})
    return {"approved_price": float(answer)}


builder = StateGraph(State)
builder.add_node("approve_price", approve_price)
builder.add_edge(START, "approve_price")
builder.add_edge("approve_price", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "lesson-3"}}

if __name__ == "__main__":
    paused = graph.invoke({"proposed_price": 100, "approved_price": 0}, config=config)
    print("PAUZA:", paused["__interrupt__"][0].value)
    finished = graph.invoke(Command(resume=95), config=config)
    print("WZNOWIENIE:", finished)
