import os
from typing import Dict, List


class NotesIndexer:
    """Parses local directory notes and extracts metadata/links."""
    def parse_directory(self, folder_path: str) -> List[Dict]:
        notes = []
        if not os.path.exists(folder_path):
            return notes
        for file in os.listdir(folder_path):
            if file.endswith(".md"):
                path = os.path.join(folder_path, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                notes.append({
                    "title": file.replace(".md", ""),
                    "content": content,
                    "links": self._extract_links(content)
                })
        return notes

    def _extract_links(self, content: str) -> List[str]:
        import re
        return re.findall(r'\[\[(.*?)\]\]', content)
