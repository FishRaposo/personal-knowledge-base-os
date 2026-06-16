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


class TestGraphExport:
    def _notes(self):
        return [
            {"id": "a", "title": "Alpha", "links": ["Beta"], "tags": ["x"]},
            {"id": "b", "title": "Beta", "links": ["Gamma"], "tags": []},
            {"id": "c", "title": "Gamma", "links": [], "tags": []},
        ]

    def test_links_resolved_by_slug(self):
        graph = BacklinksGraph()
        graph.build_graph(self._notes())
        # "Beta" in Alpha's links should resolve to node id "b".
        assert "b" in graph.adj_list["a"]
        assert graph.get_backlinks("b") == ["a"]

    def test_get_graph_nodes_and_edges(self):
        graph = BacklinksGraph()
        graph.build_graph(self._notes())
        payload = graph.get_graph()
        assert {n["id"] for n in payload["nodes"]} == {"a", "b", "c"}
        edges = {(e["source"], e["target"]) for e in payload["edges"]}
        assert ("a", "b") in edges
        assert ("b", "c") in edges

    def test_node_degrees(self):
        graph = BacklinksGraph()
        graph.build_graph(self._notes())
        nodes = {n["id"]: n for n in graph.get_graph()["nodes"]}
        assert nodes["a"]["out_degree"] == 1
        assert nodes["a"]["in_degree"] == 0
        assert nodes["b"]["in_degree"] == 1

    def test_get_outbound(self):
        graph = BacklinksGraph()
        graph.build_graph(self._notes())
        assert graph.get_outbound("a") == ["b"]

    def test_rebuild_clears_previous(self):
        graph = BacklinksGraph()
        graph.build_graph(self._notes())
        graph.build_graph([{"id": "z", "title": "Z", "links": [], "tags": []}])
        assert set(graph.adj_list) == {"z"}
