"""RTS exception hierarchy."""

from __future__ import annotations


class RTSException(Exception):
    """Base exception for recoverable RTS domain errors."""


class PluginError(RTSException):
    """Base exception for plugin registration and loading errors."""


class PluginRegistrationError(PluginError):
    """Raised when a plugin cannot be registered."""
