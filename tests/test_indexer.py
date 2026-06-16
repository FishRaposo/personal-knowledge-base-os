import os
import tempfile

from apps.api.src.indexer import (
    NotesIndexer,
    extract_tags,
    extract_wikilinks,
    slugify,
)


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

    def test_recursive_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "nested")
            os.makedirs(sub)
            with open(os.path.join(tmpdir, "top.md"), "w") as f:
                f.write("# Top")
            with open(os.path.join(sub, "deep.md"), "w") as f:
                f.write("# Deep")
            indexer = NotesIndexer()
            notes = indexer.parse_directory(tmpdir)
            ids = {n["id"] for n in notes}
            assert ids == {"top", "deep"}

    def test_note_has_id_and_chunks(self):
        indexer = NotesIndexer()
        note = indexer.parse_note("# Hello\nSome body text.", source="My Note.md")
        assert note["id"] == "my_note"
        assert note["title"] == "Hello"  # from the H1
        assert note["chunks"], "expected at least one chunk"
        assert note["chunks"][0]["note_id"] == "my_note"
        assert "content_hash" in note


class TestFrontmatterAndTags:
    def test_frontmatter_title_and_tags(self):
        indexer = NotesIndexer()
        raw = "---\ntitle: Real Title\ntags: [alpha, beta]\n---\n# Heading\nBody."
        note = indexer.parse_note(raw, source="x.md")
        assert note["title"] == "Real Title"
        assert "alpha" in note["tags"]
        assert "beta" in note["tags"]
        # Frontmatter should be stripped from the body content.
        assert "title: Real Title" not in note["content"]

    def test_inline_hashtags_extracted(self):
        tags = extract_tags("Some text #python and #ml/deep here.")
        assert "python" in tags
        assert "ml/deep" in tags

    def test_frontmatter_and_inline_tags_merge(self):
        indexer = NotesIndexer()
        raw = "---\ntags: [meta]\n---\n# T\nbody #extra"
        note = indexer.parse_note(raw, source="t.md")
        assert set(note["tags"]) >= {"meta", "extra"}

    def test_wikilink_alias_keeps_target(self):
        links = extract_wikilinks("See [[target|the alias]] here.")
        assert links == ["target"]

    def test_wikilinks_deduplicated(self):
        links = extract_wikilinks("[[a]] [[a]] [[b]]")
        assert links == ["a", "b"]

    def test_slugify(self):
        assert slugify("My Note Title") == "my_note_title"
        assert slugify("Note-Architecture") == "note_architecture"
