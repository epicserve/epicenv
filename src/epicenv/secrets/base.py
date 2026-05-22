"""Base class for secret providers."""

from abc import ABC, abstractmethod


class SecretProvider(ABC):
    """Abstract base class for secret providers."""

    @abstractmethod
    def is_available(self) -> tuple[bool, str | None]:
        """
        Check if the secret provider is available and properly configured.

        Returns:
            Tuple of (is_available, error_message).
            If available, error_message is None.
            If not available, error_message contains a description of the issue.
        """

    @abstractmethod
    def get_field(self, reference: str) -> tuple[str | None, str | None]:
        """
        Retrieve a single field value from the secret provider.

        Args:
            reference: Provider-specific reference to the secret
                      (e.g., "op://vault/item/field" for 1Password)

        Returns:
            Tuple of (value, error_message).
            If successful, error_message is None.
            If failed, value is None and error_message contains the error.
        """

    @abstractmethod
    def get_fields(self, reference: str, fields: list[str]) -> tuple[dict[str, str] | None, str | None]:
        """
        Retrieve multiple fields from the secret provider.

        Args:
            reference: Base reference to the secret item
                      (e.g., "op://vault/item" for 1Password)
            fields: List of field names to retrieve

        Returns:
            Tuple of (values_dict, error_message).
            If successful, values_dict maps field names to values, error_message is None.
            If failed, values_dict is None and error_message contains the error.
        """
