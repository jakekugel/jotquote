# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.


class ApiException(Exception):  # noqa: N818
    """Base class for all user-facing errors raised by :mod:`jotquote.api`.

    Callers that embed jotquote should catch this type to handle any
    recoverable API error uniformly.  Programmer-misuse errors such as passing
    the wrong type are raised as :class:`TypeError` or :class:`ValueError`
    instead and are *not* subclasses of ``ApiException``.
    """


class ConfigError(ApiException):
    """Raised for problems loading or interpreting settings.conf."""


class QuoteValidationError(ApiException):
    """Raised when parsing a quote, tag, or field fails validation.

    Attributes:
        field (str | None): Which field the error applies to -- ``'quote'``,
            ``'author'``, ``'publication'``, or ``'tags'``.  ``None`` for
            structural errors (e.g. wrong pipe count).
    """

    def __init__(self, message, field=None):
        """Create a validation error.

        Args:
            message (str): Human-readable error message.
            field (str | None): The field name this error applies to, or
                ``None`` for structural errors.
        """
        super().__init__(message)
        self.field = field


class QuoteNotFoundError(ApiException):
    """Raised when a quote selector (line number, hash) matches no quote."""


class DuplicateQuoteError(ApiException):
    """Raised when adding a quote that is already present in the file."""


class ConcurrentModificationError(ApiException):
    """Raised when the quote file's SHA-256 no longer matches the caller's expectation.

    Attributes:
        expected_sha256 (str): The hash the caller passed in.
        current_sha256 (str | None): The file's current hash on disk.  ``None``
            if the check failed before a current hash could be computed.
    """

    def __init__(self, message, expected_sha256, current_sha256=None):
        """Create a concurrent modification error.

        Args:
            message (str): Human-readable error message.
            expected_sha256 (str): The hash the caller passed in.
            current_sha256 (str | None): The hash the file currently has.
        """
        super().__init__(message)
        self.expected_sha256 = expected_sha256
        self.current_sha256 = current_sha256


class StorageError(ApiException):
    """Raised for I/O failures, missing quote files, and backup sanity check failures."""
