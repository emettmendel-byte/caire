"""API tests for decision tree CRUD and generation."""

import pytest
from fastapi.testclient import TestClient

from shared.schemas import DecisionTree, DecisionNode, Edge, NodeType


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "CAIRE"
    assert "api" in data


def test_list_trees_empty(client: TestClient):
    r = client.get("/api/trees/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_get_tree(client: TestClient):
    tree = DecisionTree(
        id="test-tree-1",
        version="1.0.0",
        name="Test Triage Tree",
        description="Sample",
        nodes=[
            DecisionNode(id="root", type=NodeType.ROOT, label="Start"),
            DecisionNode(id="out", type=NodeType.OUTCOME, label="End"),
        ],
        edges=[Edge(source_id="root", target_id="out", label="OK")],
        root_id="root",
    )
    r = client.post("/api/trees/", json=tree.model_dump(mode="json"))
    assert r.status_code == 201
    got = r.json()
    assert got["id"] == tree.id
    assert got["name"] == tree.name

    r2 = client.get(f"/api/trees/{tree.id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == tree.id


def test_delete_tree(client: TestClient):
    tree = DecisionTree(
        id="to-delete",
        version="1.0.0",
        name="Delete me",
        nodes=[],
        edges=[],
    )
    client.post("/api/trees/", json=tree.model_dump(mode="json"))
    r = client.delete("/api/trees/to-delete")
    assert r.status_code == 204
    r2 = client.get("/api/trees/to-delete")
    assert r2.status_code == 404


def test_generate_tree_no_file(client: TestClient):
    r = client.post("/api/trees/generate")
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == "generated"
    assert "nodes" in data
    assert len(data["nodes"]) >= 1
