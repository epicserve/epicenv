"""Base class for framework integrations."""

from abc import ABC, abstractmethod


class FrameworkIntegration(ABC):
    """Abstract base class for framework-specific integrations."""

    @abstractmethod
    def is_available(self) -> tuple[bool, str | None]:
        """
        Check if the framework is available (installed).

        Returns:
            Tuple of (is_available, error_message).
            If available, error_message is None.
            If not available, error_message contains a description of the issue.
        """

    @abstractmethod
    def execute(self, **kwargs):
        """
        Execute the framework-specific integration operation.

        Subclasses define their own keyword arguments and return value.

        Raises:
            Exception: If the operation fails.
        """
