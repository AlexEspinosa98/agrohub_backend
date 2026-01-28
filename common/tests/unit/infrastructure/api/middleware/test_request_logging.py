"""
Unit tests for middleware.RequestLoggingMiddleware.

Tests middleware functionality for request logging.
"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi import Request, Response
import pytest

from common.infrastructure.api import middleware


class TestRequestLoggingMiddleware:
    """Test cases for middleware.RequestLoggingMiddleware."""

    @pytest.fixture
    def setup_request_logging_middleware(self) -> middleware.RequestLoggingMiddleware:
        """Create middleware instance."""
        app = Mock()
        return middleware.RequestLoggingMiddleware(app)

    @pytest.fixture
    def mock_request(self) -> Mock:
        """Create mock request."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        request.headers = {
            "X-Request-ID": "test-request-123",
            "user-agent": "test-client/1.0",
        }
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_response(self) -> Mock:
        """Create mock response."""
        response = Mock(spec=Response)
        response.status_code = 200
        return response

    @pytest.fixture
    def mock_call_next(self, mock_response: Mock) -> AsyncMock:
        """Create mock call_next function."""
        call_next = AsyncMock()
        call_next.return_value = mock_response
        return call_next

    @pytest.mark.asyncio
    async def test_successful_request_logging(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_response: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test logging for successful request."""
        # Arrange
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            result: Response = await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert
            assert result == mock_response
            mock_call_next.assert_called_once_with(mock_request)

            # Verify logger was called
            mock_get_logger.assert_called_with("api")
            assert mock_logger.info.call_count == 2  # Start and completion logs

    @pytest.mark.asyncio
    async def test_request_start_logging_details(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test request start logging contains correct details."""
        # Arrange
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert - Check first call (start logging)
            start_call = mock_logger.info.call_args_list[0]
            assert start_call[0][0] == "Request started"

            extra = start_call[1]["extra"]
            assert extra["request_id"] == "test-request-123"
            assert extra["method"] == "GET"
            assert extra["path"] == "/api/test"
            assert extra["client_ip"] == "127.0.0.1"
            assert extra["user_agent"] == "test-client/1.0"

    @pytest.mark.asyncio
    async def test_request_completion_logging_details(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_response: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test request completion logging contains correct details."""
        # Arrange
        with (
            patch("logging.getLogger") as mock_get_logger,
            patch("time.time", side_effect=[1000.0, 1000.5]),
        ):  # 500ms duration
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert - Check second call (completion logging)
            completion_call = mock_logger.info.call_args_list[1]
            assert completion_call[0][0] == "Request completed"

            extra = completion_call[1]["extra"]
            assert extra["request_id"] == "test-request-123"
            assert extra["status_code"] == 200
            assert extra["process_time_ms"] == 500.0

    @pytest.mark.asyncio
    async def test_request_missing_headers(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test logging with missing request headers."""
        # Arrange
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/create"
        request.headers = {}  # No headers
        request.client = None  # No client info

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            await setup_request_logging_middleware.dispatch(request, mock_call_next)

            # Assert
            start_call = mock_logger.info.call_args_list[0]
            extra = start_call[1]["extra"]
            assert extra["request_id"] == "unknown"
            assert extra["client_ip"] == "unknown"
            assert extra["user_agent"] == "unknown"

    @pytest.mark.asyncio
    async def test_request_exception_handling(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
    ) -> None:
        """Test logging when request raises exception."""
        # Arrange
        call_next = AsyncMock()
        call_next.side_effect = ValueError("Test error")

        with (
            patch("logging.getLogger") as mock_get_logger,
            patch("time.time", side_effect=[1000.0, 1000.2]),
        ):  # 200ms duration
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act & Assert
            with pytest.raises(ValueError, match="Test error"):
                await setup_request_logging_middleware.dispatch(mock_request, call_next)

            # Verify error logging
            assert mock_logger.error.call_count == 1
            error_call = mock_logger.error.call_args
            assert error_call[0][0] == "Request failed"

            extra = error_call[1]["extra"]
            assert extra["request_id"] == "test-request-123"
            assert extra["error"] == "Test error"
            assert extra["process_time_ms"] == 200.0
            assert error_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_process_time_calculation(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test process time calculation accuracy."""
        # Arrange
        with (
            patch("logging.getLogger") as mock_get_logger,
            patch("time.time", side_effect=[1000.0, 1000.123]),
        ):  # 123ms duration
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert
            completion_call = mock_logger.info.call_args_list[1]
            extra = completion_call[1]["extra"]
            assert extra["process_time_ms"] == 123.0

    @pytest.mark.asyncio
    async def test_logger_name_consistency(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that consistent logger name is used."""
        # Arrange
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert
            mock_get_logger.assert_called_with("api")

    @pytest.mark.asyncio
    async def test_request_id_consistency(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that request ID is consistent across all log entries."""
        # Arrange
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Act
            await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert
            start_extra = mock_logger.info.call_args_list[0][1]["extra"]
            completion_extra = mock_logger.info.call_args_list[1][1]["extra"]

            assert start_extra["request_id"] == completion_extra["request_id"]
            assert start_extra["request_id"] == "test-request-123"

    @pytest.mark.asyncio
    async def test_response_passthrough(
        self,
        setup_request_logging_middleware: middleware.RequestLoggingMiddleware,
        mock_request: Mock,
        mock_response: Mock,
        mock_call_next: AsyncMock,
    ) -> None:
        """Test that middleware passes through response unchanged."""
        # Arrange
        with patch("logging.getLogger"):
            # Act
            result = await setup_request_logging_middleware.dispatch(
                mock_request, mock_call_next
            )

            # Assert
            assert result is mock_response
            assert result.status_code == 200
