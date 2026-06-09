from typing import Dict, List, Set


class BacklinksGraph:
    """Tracks linkages and generates layout parameters for note nodes."""
    def __init__(self):
        self.adj_list: Dict[str, Set[str]] = {}

    def build_graph(self, notes: List[Dict]):
        for note in notes:
            title = note["title"]
            if title not in self.adj_list:
                self.adj_list[title] = set()
            for link in note["links"]:
                self.adj_list[title].add(link)

    def get_backlinks(self, target_title: str) -> List[str]:
        backlinks = []
        for src, dests in self.adj_list.items():
            if target_title in dests:
                backlinks.append(src)
        return backlinks
