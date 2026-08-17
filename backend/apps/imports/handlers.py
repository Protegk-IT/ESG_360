from abc import ABC, abstractmethod

from django.core.exceptions import ValidationError


class ImportHandler(ABC):
    """
    Contract for concrete import handlers.

    Future modules such as Answers, Datapoints, Framework Nodes,
    Stakeholders and Emission Factors will implement this contract.
    """

    @abstractmethod
    def validate_row(self, raw_data):
        """
        Validate and normalize one parsed spreadsheet row.

        Args:
            raw_data (dict):
                Raw JSON-safe data produced by the generic parser.

        Returns:
            tuple[dict, dict]:
                normalized_data, errors
        """
        raise NotImplementedError

    def validate_batch(self, rows):
        """
        Optional batch-level validation.

        `rows` contains ImportRow instances.

        Concrete handlers can override this when they need
        cross-row or batch-level validation.
        """
        return None

    @abstractmethod
    def commit(self, batch):
        """
        Commit a previously validated batch transactionally.

        Concrete handlers implement destination-specific
        persistence here.
        """
        raise NotImplementedError


class ImportHandlerRegistry:
    """
    Registry mapping ImportBatch import types to handlers.

    Example:

        ImportHandlerRegistry.register(
            "ANSWERS",
            AnswersImportHandler,
        )

    Concrete handlers should be registered by their own
    feature/module when those processors are implemented.
    """

    _handlers = {}

    @classmethod
    def register(cls, import_type, handler):
        """
        Register a handler for an import type.
        """

        if not isinstance(import_type, str):
            raise TypeError(
                "import_type must be a string."
            )

        if not isinstance(handler, type):
            raise TypeError(
                "handler must be a class."
            )

        if not issubclass(handler, ImportHandler):
            raise TypeError(
                "handler must inherit from ImportHandler."
            )

        cls._handlers[import_type] = handler

    @classmethod
    def get_handler(cls, import_type):
        """
        Return an instantiated handler for the import type.
        """

        handler = cls._handlers.get(import_type)

        if handler is None:
            raise ValidationError(
                {
                    "import_type": (
                        f"No import handler is registered for "
                        f"{import_type}."
                    )
                }
            )

        return handler()

    @classmethod
    def clear(cls):
        """
        Clear the registry.

        Primarily useful for isolated tests.
        """

        cls._handlers.clear()


class FakeAnswersImportHandler(ImportHandler):
    """
    Test-only handler for validating the generic
    import-batch infrastructure.
    """

    def validate_row(self, raw_data):
        errors = {}

        facility_code = raw_data.get("facility_code")
        quantity = raw_data.get("quantity")

        if not facility_code:
            errors["facility_code"] = [
                "Facility code is required."
            ]

        if quantity is None:
            errors["quantity"] = [
                "Quantity is required."
            ]
        elif quantity < 0:
            errors["quantity"] = [
                "Quantity cannot be negative."
            ]

        return raw_data, errors

    def commit(self, batch):
        return None