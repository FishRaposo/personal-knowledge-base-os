import os
import tempfile

from apps.api.src.indexer import NotesIndexer


class TestNotesIndexer:
    def test_parse_directory_finds_md_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "note1.md"), "w") as f:
                f.write("Content 1")
            with open(os.path.join(tmpdir, "note2.md"), "w") as f:
                f.write("Content 2")
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("Not a note")

            indexer = NotesIndexer()
            notes = indexer.parse_directory(tmpdir)
            assert len(notes) == 2
            assert notes[0]["title"] in ["note1", "note2"]

    def test_parse_directory_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = NotesIndexer()
            notes = indexer.parse_directory(tmpdir)
            assert notes == []

    def test_parse_directory_nonexistent(self):
        indexer = NotesIndexer()
        notes = indexer.parse_directory("/nonexistent/path/xyz")
        assert notes == []

    def test_extract_wikilinks(self):
        indexer = NotesIndexer()
        links = indexer._extract_links("See [[Note A]] and [[Note B]] for details.")
        assert len(links) == 2
        assert "Note A" in links
        assert "Note B" in links

    def test_extract_no_links(self):
        indexer = NotesIndexer()
        links = indexer._extract_links("Plain text with no links.")
        assert links == []

    def test_extract_links_from_content(self):
        indexer = NotesIndexer()
        links = indexer._extract_links("[[one]] [[two]] [[three]]")
        assert len(links) == 3

    def test_note_has_correct_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.md"), "w") as f:
                f.write("Hello world [[Link1]]")

            indexer = NotesIndexer()
            notes = indexer.parse_directory(tmpdir)
            assert len(notes) == 1
            note = notes[0]
            assert "title" in note
            assert "content" in note
            assert "links" in note
            assert note["title"] == "test"
            assert "Hello world" in note["content"]
            assert "Link1" in note["links"]
