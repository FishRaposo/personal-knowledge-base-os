import os
import sys

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../apps/api/src")
    ),
)

from graph import BacklinksGraph
from indexer import NotesIndexer


def main():
    os.makedirs("temp_vault", exist_ok=True)
    with open("temp_vault/Hermes.md", "w") as f:
        f.write("Hermes is an agent framework. It uses [[Celery]] for jobs.")
    with open("temp_vault/Celery.md", "w") as f:
        f.write("Celery runs task tasks. Linked from [[Hermes]].")

    print("--- Running Knowledge Base Indexer ---")
    indexer = NotesIndexer()
    graph = BacklinksGraph()

    notes = indexer.parse_directory("temp_vault")
    graph.build_graph(notes)

    print(f"Notes linked from Hermes: {notes[0]['links']}")
    print(f"Backlinks for Celery: {graph.get_backlinks('Celery')}")

    try:
        os.remove("temp_vault/Hermes.md")
        os.remove("temp_vault/Celery.md")
        os.rmdir("temp_vault")
    except OSError:
        pass


if __name__ == "__main__":
    main()
