from apps.api.src.graph import BacklinksGraph


class TestBacklinksGraph:
    def test_build_graph_adds_edges(self):
        graph = BacklinksGraph()
        notes = [
            {"title": "Note1", "links": ["Note2", "Note3"]},
            {"title": "Note2", "links": ["Note3"]},
            {"title": "Note3", "links": []},
        ]
        graph.build_graph(notes)
        assert "Note1" in graph.adj_list
        assert "Note2" in graph.adj_list["Note1"]
        assert "Note3" in graph.adj_list["Note1"]

    def test_get_backlinks_returns_sources(self):
        graph = BacklinksGraph()
        notes = [
            {"title": "A", "links": ["B"]},
            {"title": "B", "links": []},
        ]
        graph.build_graph(notes)
        backlinks = graph.get_backlinks("B")
        assert "A" in backlinks

    def test_get_backlinks_no_links(self):
        graph = BacklinksGraph()
        notes = [
            {"title": "A", "links": []},
            {"title": "B", "links": ["A"]},
        ]
        graph.build_graph(notes)
        backlinks = graph.get_backlinks("B")
        assert backlinks == []

    def test_empty_graph_build(self):
        graph = BacklinksGraph()
        graph.build_graph([])
        assert graph.adj_list == {}

    def test_bidirectional_links(self):
        graph = BacklinksGraph()
        notes = [
            {"title": "A", "links": ["B"]},
            {"title": "B", "links": ["A"]},
        ]
        graph.build_graph(notes)
        assert graph.get_backlinks("A") == ["B"]
        assert graph.get_backlinks("B") == ["A"]

    def test_orphaned_link(self):
        graph = BacklinksGraph()
        notes = [
            {"title": "A", "links": ["C"]},
            {"title": "B", "links": []},
        ]
        graph.build_graph(notes)
        assert graph.get_backlinks("C") == ["A"]

    def test_self_reference(self):
        graph = BacklinksGraph()
        notes = [{"title": "A", "links": ["A"]}]
        graph.build_graph(notes)
        backlinks = graph.get_backlinks("A")
        assert "A" in backlinks
