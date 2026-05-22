"""Framework integration module for epicenv."""

from .base import FrameworkIntegration
from .django import DjangoSuperuserIntegration

__all__ = ["FrameworkIntegration", "DjangoSuperuserIntegration"]
