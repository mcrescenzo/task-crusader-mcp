"""Tests for domain result types."""

import pytest

from task_crusade_mcp.domain.entities.result_types import (
    DomainError,
    DomainErrorType,
    DomainSuccess,
)


class TestDomainResult:
    """Tests for DomainResult."""

    def test_success_result(self):
        """Test creating a success result."""
        result = DomainSuccess.create(data={"id": "123"})

        assert result.success is True
        assert result.is_success is True
        assert result.is_failure is False
        assert result.data == {"id": "123"}
        assert result.error_message is None

    def test_error_result(self):
        """Test creating an error result."""
        result = DomainError.validation_error("Invalid input")

        assert result.success is False
        assert result.is_success is False
        assert result.is_failure is True
        assert result.error_message == "Invalid input"
        assert result.error_type == DomainErrorType.VALIDATION_ERROR

    def test_not_found_error(self):
        """Test creating a not found error."""
        result = DomainError.not_found("Campaign", "abc123")

        assert result.is_failure is True
        assert result.error_type == DomainErrorType.NOT_FOUND
        assert "Campaign" in result.error_message
        assert "abc123" in result.error_message

    def test_already_exists_error(self):
        """Test creating an already exists error."""
        result = DomainError.already_exists("Campaign", "test-campaign")

        assert result.is_failure is True
        assert result.error_type == DomainErrorType.ALREADY_EXISTS
        assert "already exists" in result.error_message

    def test_get_data_or_raise_success(self):
        """Test get_data_or_raise with success."""
        result = DomainSuccess.create(data={"value": 42})
        data = result.get_data_or_raise()
        assert data == {"value": 42}

    def test_get_data_or_raise_failure(self):
        """Test get_data_or_raise with failure."""
        result = DomainError.validation_error("Error")
        with pytest.raises(ValueError):
            result.get_data_or_raise()

    def test_get_data_or_default(self):
        """Test get_data_or_default."""
        success_result = DomainSuccess.create(data={"value": 42})
        assert success_result.get_data_or_default({}) == {"value": 42}

        error_result = DomainError.validation_error("Error")
        assert error_result.get_data_or_default({"default": True}) == {"default": True}
