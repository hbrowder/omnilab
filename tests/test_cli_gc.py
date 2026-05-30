"""Tests for the orphan garbage collection CLI tool."""

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add backend/ to path so imports work
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from cli.gc import (
    connect_docker,
    find_orphans,
    delete_orphans,
    is_container_running,
    is_network_alive,
    is_qemu_running,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite DB with test schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    db_path = Path(path)
    
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE labs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'stopped',
            topology TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            lab_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            image TEXT,
            status TEXT DEFAULT 'stopped',
            config TEXT DEFAULT '{}',
            x REAL DEFAULT 0,
            y REAL DEFAULT 0,
            console_port INTEGER,
            created_at TEXT,
            console_type TEXT NOT NULL DEFAULT 'pty',
            vnc_port INTEGER,
            rdp_host TEXT,
            rdp_port INTEGER,
            FOREIGN KEY(lab_id) REFERENCES labs(id)
        )
    """)
    conn.execute("""
        CREATE TABLE links (
            id TEXT PRIMARY KEY,
            lab_id TEXT NOT NULL,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            FOREIGN KEY(lab_id) REFERENCES labs(id)
        )
    """)
    conn.commit()
    conn.close()
    
    yield db_path
    
    db_path.unlink()


def test_find_orphans_with_stopped_docker_node(temp_db):
    """Orphan detection finds stopped docker nodes with no live container."""
    conn = sqlite3.connect(str(temp_db))
    
    # Insert a stopped docker node (created > 24h ago)
    conn.execute(
        "INSERT INTO labs (id, name, status) VALUES (?, ?, ?)",
        ("lab-1", "Test Lab", "stopped")
    )
    conn.execute(
        "INSERT INTO nodes (id, lab_id, name, type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("node-1", "lab-1", "orphan-node", "docker", "stopped", "2024-01-01T00:00:00Z")
    )
    conn.commit()
    conn.close()
    
    # Mock Docker client that reports no container exists
    mock_docker = MagicMock()
    mock_docker.containers.get.side_effect = Exception("Container not found")
    mock_docker.networks.get.side_effect = Exception("Network not found")
    
    orphaned_labs, orphaned_nodes = find_orphans(temp_db, mock_docker, min_age_hours=1)
    
    assert len(orphaned_nodes) == 1
    assert orphaned_nodes[0]["id"] == "node-1"
    assert orphaned_nodes[0]["type"] == "docker"
    assert "no live container" in orphaned_nodes[0]["reason"]
    
    assert len(orphaned_labs) == 1
    assert orphaned_labs[0]["id"] == "lab-1"
    assert "no live network" in orphaned_labs[0]["reason"]


def test_find_orphans_with_running_container_excludes_node(temp_db):
    """Running containers are NOT detected as orphans."""
    conn = sqlite3.connect(str(temp_db))
    
    conn.execute(
        "INSERT INTO labs (id, name, status) VALUES (?, ?, ?)",
        ("lab-2", "Live Lab", "stopped")
    )
    conn.execute(
        "INSERT INTO nodes (id, lab_id, name, type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("node-2", "lab-2", "live-node", "docker", "stopped", "2024-01-01T00:00:00Z")
    )
    conn.commit()
    conn.close()
    
    # Mock Docker client that reports container IS running
    mock_docker = MagicMock()
    mock_container = Mock()
    mock_container.status = "running"
    mock_docker.containers.get.return_value = mock_container
    
    orphaned_labs, orphaned_nodes = find_orphans(temp_db, mock_docker, min_age_hours=1)
    
    # Node should NOT be in orphan list (container is running)
    assert len(orphaned_nodes) == 0
    # Lab should NOT be orphaned either (has a live node)
    assert len(orphaned_labs) == 0


def test_find_orphans_with_null_created_at(temp_db):
    """NULL created_at values are treated as orphan candidates (legacy data)."""
    conn = sqlite3.connect(str(temp_db))
    
    conn.execute(
        "INSERT INTO labs (id, name, status, created_at) VALUES (?, ?, ?, ?)",
        ("lab-3", "Legacy Lab", "stopped", None)
    )
    conn.execute(
        "INSERT INTO nodes (id, lab_id, name, type, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("node-3", "lab-3", "legacy-node", "docker", "stopped", None)
    )
    conn.commit()
    conn.close()
    
    # Mock Docker with no live artifacts
    mock_docker = MagicMock()
    mock_docker.containers.get.side_effect = Exception("Not found")
    mock_docker.networks.get.side_effect = Exception("Not found")
    
    orphaned_labs, orphaned_nodes = find_orphans(temp_db, mock_docker, min_age_hours=24)
    
    # Should detect both as orphans despite NULL created_at
    assert len(orphaned_nodes) == 1
    assert orphaned_nodes[0]["id"] == "node-3"
    
    assert len(orphaned_labs) == 1
    assert orphaned_labs[0]["id"] == "lab-3"


def test_delete_orphans(temp_db):
    """delete_orphans removes specified labs and nodes from DB."""
    conn = sqlite3.connect(str(temp_db))
    
    # Insert test data
    conn.execute(
        "INSERT INTO labs (id, name, status) VALUES (?, ?, ?)",
        ("lab-4", "Doomed Lab", "stopped")
    )
    conn.execute(
        "INSERT INTO nodes (id, lab_id, name, type, status) VALUES (?, ?, ?, ?, ?)",
        ("node-4a", "lab-4", "node-a", "docker", "stopped")
    )
    conn.execute(
        "INSERT INTO nodes (id, lab_id, name, type, status) VALUES (?, ?, ?, ?, ?)",
        ("node-4b", "lab-4", "node-b", "docker", "stopped")
    )
    conn.execute(
        "INSERT INTO links (id, lab_id, source_node_id, target_node_id) VALUES (?, ?, ?, ?)",
        ("link-1", "lab-4", "node-4a", "node-4b")
    )
    conn.commit()
    
    # Verify data exists
    assert conn.execute("SELECT COUNT(*) FROM labs WHERE id = 'lab-4'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM nodes WHERE lab_id = 'lab-4'").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM links WHERE lab_id = 'lab-4'").fetchone()[0] == 1
    conn.close()
    
    # Delete orphans
    orphans_labs = [{"id": "lab-4", "name": "Doomed Lab"}]
    orphans_nodes = [{"id": "node-4a"}, {"id": "node-4b"}]
    
    deleted_labs, deleted_nodes = delete_orphans(temp_db, orphans_labs, orphans_nodes)
    
    assert deleted_labs == 1
    assert deleted_nodes == 2
    
    # Verify deletion
    conn = sqlite3.connect(str(temp_db))
    assert conn.execute("SELECT COUNT(*) FROM labs WHERE id = 'lab-4'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM nodes WHERE lab_id = 'lab-4'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM links WHERE lab_id = 'lab-4'").fetchone()[0] == 0
    conn.close()


def test_is_qemu_running(tmp_path):
    """is_qemu_running checks for .pid files in ~/.omnilab/labs/."""
    # Mock the home directory structure
    labs_dir = tmp_path / ".omnilab" / "labs"
    labs_dir.mkdir(parents=True)
    
    # Create a pid file for node-5
    pid_file = labs_dir / "node-5.pid"
    pid_file.write_text("12345")
    
    # Temporarily override Path.home() for this test
    import cli.gc as gc_module
    original_home = Path.home
    gc_module.Path.home = lambda: tmp_path
    
    try:
        assert gc_module.is_qemu_running("node-5") is True
        assert gc_module.is_qemu_running("node-999") is False
    finally:
        gc_module.Path.home = original_home
