"""Tests for CRE-49: ENOSPC (disk full) error handling.

Verifies that DockerProvisioner detects errno 28 / "no space left" errors
and surfaces them as DiskFullError with actionable guidance.
"""
import errno
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add backend/ to path so we can import the provisioner
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.docker_provisioner import (
    DiskFullError,
    DockerProvisioner,
    DockerProvisionerError,
    ImageNotFound,
    _is_disk_full_error,
)


class TestDiskFullDetection:
    """Unit tests for _is_disk_full_error() helper."""

    def test_detects_oserror_enospc(self):
        """Direct OSError with errno.ENOSPC should be detected."""
        exc = OSError(errno.ENOSPC, "No space left on device")
        assert _is_disk_full_error(exc)

    def test_detects_docker_api_error_with_explanation(self):
        """Docker APIError with 'no space left' in explanation."""
        exc = Mock()
        exc.explanation = "Error response: no space left on device"
        assert _is_disk_full_error(exc)

    def test_detects_enospc_in_exception_string(self):
        """Fallback: scan str(exc) for ENOSPC markers."""
        exc = Exception("docker: write /var/lib/docker: no space left on device")
        assert _is_disk_full_error(exc)

    def test_detects_errno_28_in_string(self):
        """Fallback: recognize 'errno 28' in exception message."""
        exc = RuntimeError("write failed: [Errno 28] No space left")
        assert _is_disk_full_error(exc)

    def test_ignores_unrelated_oserror(self):
        """OSError with different errno should NOT be flagged."""
        exc = OSError(errno.EACCES, "Permission denied")
        assert not _is_disk_full_error(exc)

    def test_ignores_unrelated_exception(self):
        """Generic exception with no disk-full markers."""
        exc = ValueError("Invalid configuration")
        assert not _is_disk_full_error(exc)


class TestDockerProvisionerEnospc:
    """Integration tests for ENOSPC handling in DockerProvisioner methods."""

    @pytest.fixture
    def mock_client(self):
        """Mock docker client for injection."""
        client = MagicMock()
        client.ping.return_value = True
        return client

    def test_ensure_image_raises_disk_full_on_oserror(self, mock_client):
        """ensure_image wraps OSError(ENOSPC) as DiskFullError."""
        mock_client.images.get.side_effect = ImageNotFound("not found")
        mock_client.api.pull.side_effect = OSError(errno.ENOSPC, "No space left")

        provisioner = DockerProvisioner(client=mock_client)

        with pytest.raises(DiskFullError) as exc_info:
            import asyncio
            asyncio.run(provisioner.ensure_image("alpine:latest"))

        assert "no disk space left" in str(exc_info.value).lower()
        assert "docker system prune" in str(exc_info.value)

    def test_ensure_image_raises_disk_full_on_pull_error_event(self, mock_client):
        """ensure_image detects 'no space left' in pull event error field."""
        mock_client.images.get.side_effect = ImageNotFound("not found")
        mock_client.api.pull.return_value = [
            {"status": "Pulling fs layer", "id": "abc123"},
            {"error": "write /var/lib/docker: no space left on device"}
        ]

        provisioner = DockerProvisioner(client=mock_client)

        with pytest.raises(DiskFullError) as exc_info:
            import asyncio
            asyncio.run(provisioner.ensure_image("kalilinux/kali-rolling"))

        assert "no disk space left" in str(exc_info.value).lower()

    def test_start_node_raises_disk_full_on_enospc(self, mock_client):
        """start_node wraps container creation ENOSPC as DiskFullError."""
        mock_client.containers.run.side_effect = OSError(errno.ENOSPC, "No space left")

        provisioner = DockerProvisioner(client=mock_client)

        with pytest.raises(DiskFullError) as exc_info:
            import asyncio
            asyncio.run(provisioner.start_node(
                node_id="test-node",
                lab_id="test-lab",
                image="alpine:latest",
                name="test"
            ))

        assert "cannot start node" in str(exc_info.value).lower()
        assert "no disk space left" in str(exc_info.value).lower()

    def test_start_node_reraises_non_disk_errors(self, mock_client):
        """start_node preserves non-ENOSPC exceptions."""
        mock_client.containers.run.side_effect = RuntimeError("Image not found")

        provisioner = DockerProvisioner(client=mock_client)

        with pytest.raises(RuntimeError) as exc_info:
            import asyncio
            asyncio.run(provisioner.start_node(
                node_id="test-node",
                lab_id="test-lab",
                image="missing:latest",
                name="test"
            ))

        assert "Image not found" in str(exc_info.value)
        # Should NOT be wrapped as DiskFullError
        assert not isinstance(exc_info.value, DiskFullError)


class TestHealthEndpointDiskWarnings:
    """Test /api/health/metrics disk warning logic (CRE-49)."""

    @patch("api.health.psutil.disk_usage")
    @patch("api.health.HAS_PSUTIL", True)
    def test_critical_warning_at_95_percent(self, mock_disk_usage):
        """Metrics endpoint returns disk_critical=True at 95%+ usage."""
        mock_disk_usage.return_value = Mock(
            total=1000 * (1024**3),  # 1000 GB
            used=950 * (1024**3),    # 950 GB used
            free=50 * (1024**3),     # 50 GB free
            percent=95.0
        )

        # Import and call the endpoint
        from api.health import get_system_metrics
        import asyncio
        result = asyncio.run(get_system_metrics())

        assert result["disk_critical"] is True
        assert "CRITICAL" in result["disk_warning"]
        assert "docker system prune" in result["disk_warning"]

    @patch("api.health.psutil.disk_usage")
    @patch("api.health.HAS_PSUTIL", True)
    def test_warning_at_90_percent(self, mock_disk_usage):
        """Metrics endpoint returns disk_warning at 90-94% usage."""
        mock_disk_usage.return_value = Mock(
            total=1000 * (1024**3),
            used=920 * (1024**3),
            free=80 * (1024**3),
            percent=92.0
        )

        from api.health import get_system_metrics
        import asyncio
        result = asyncio.run(get_system_metrics())

        assert result["disk_critical"] is False
        assert result["disk_warning"] is not None
        assert "WARNING" in result["disk_warning"]

    @patch("api.health.psutil.disk_usage")
    @patch("api.health.HAS_PSUTIL", True)
    def test_no_warning_at_normal_usage(self, mock_disk_usage):
        """No warnings when disk usage is <80%."""
        mock_disk_usage.return_value = Mock(
            total=1000 * (1024**3),
            used=600 * (1024**3),
            free=400 * (1024**3),
            percent=60.0
        )

        from api.health import get_system_metrics
        import asyncio
        result = asyncio.run(get_system_metrics())

        assert result["disk_critical"] is False
        assert result["disk_warning"] is None


class TestLabCreationPreflightCheck:
    """Test /api/labs POST pre-flight disk check (CRE-49)."""

    @patch("api.labs.shutil.disk_usage")
    def test_lab_creation_blocked_at_low_disk(self, mock_disk_usage):
        """Lab creation returns HTTP 507 when <10% disk free."""
        mock_disk_usage.return_value = Mock(
            total=1000 * (1024**3),
            used=920 * (1024**3),
            free=80 * (1024**3)  # 8% free
        )

        from api.labs import create_lab, LabCreate
        from fastapi import HTTPException
        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_lab(LabCreate(name="test", description="")))

        assert exc_info.value.status_code == 507
        assert "only" in exc_info.value.detail.lower()
        assert "disk space" in exc_info.value.detail.lower()

    @patch("api.labs.shutil.disk_usage")
    @patch("api.labs.get_db")
    def test_lab_creation_allowed_at_normal_disk(self, mock_get_db, mock_disk_usage):
        """Lab creation proceeds when >=10% disk free."""
        mock_disk_usage.return_value = Mock(
            total=1000 * (1024**3),
            used=700 * (1024**3),
            free=300 * (1024**3)  # 30% free
        )

        # Mock DB operations — execute/commit/rollback are awaited in the handler
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_get_db.return_value.__aiter__.return_value = [mock_db]

        from api.labs import create_lab, LabCreate
        import asyncio

        result = asyncio.run(create_lab(LabCreate(name="test", description="")))

        assert "id" in result
        assert result["name"] == "test"
        # DB insert should have been called
        mock_db.execute.assert_called()
