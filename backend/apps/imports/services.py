from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.imports.handlers import ImportHandlerRegistry
from apps.imports.parser import ExcelParser
from apps.modules.models import Module

from apps.core.models import ActivityLog
from apps.core.thread_local import get_current_request

from .models import ImportBatch, ImportRow


class ImportBatchService:
    """
    Service responsible for validating and committing import batches.

    Lifecycle:

        UPLOADED
            ↓
        VALIDATING
            ↓
        VALIDATED
            ↓
        COMMITTED

    Failed validation:

        VALIDATING
            ↓
        FAILED
    """

    @staticmethod
    def _log_activity(batch, action, changes=None):
        """
        Create a lifecycle ActivityLog entry for an ImportBatch.

        We intentionally use the existing ActivityLog action choices
        instead of modifying the global ActivityLog implementation.

        Import lifecycle events are identified using the `event`
        value inside the changes JSON.
        """

        request = get_current_request()

        user = None
        ip_address = None
        user_agent = ""
        request_path = ""

        if request is not None:
            if (
                getattr(request, "user", None)
                and request.user.is_authenticated
            ):
                user = request.user

            ip_address = request.META.get("REMOTE_ADDR")

            user_agent = request.META.get(
                "HTTP_USER_AGENT",
                "",
            )

            request_path = request.path

        ActivityLog.objects.create(
            user=user or batch.uploaded_by,
            action=action,
            model_name="ImportBatch",
            object_id=str(batch.pk),
            object_repr=str(batch),
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
        )

    @staticmethod
    @transaction.atomic
    def validate_batch(batch):
        """
        Validate every row in an import batch using the registered handler.

        Lifecycle:

            UPLOADED / FAILED
                    ↓
                VALIDATING
                    ↓
            VALIDATED / FAILED

        Validation never writes to destination business tables.
        """

        if batch.status == ImportBatch.Status.COMMITTED:
            raise ValidationError(
                "A committed batch cannot be validated again."
            )

        if batch.status not in (
            ImportBatch.Status.UPLOADED,
            ImportBatch.Status.FAILED,
        ):
            raise ValidationError(
                f"Batch cannot be validated from status "
                f"{batch.status}."
            )

        # Get the concrete handler.
        #
        # If no handler is registered for this import type,
        # ImportHandlerRegistry raises a ValidationError.
        handler = ImportHandlerRegistry.get_handler(
            batch.import_type
        )

        # Mark batch as currently validating.
        batch.status = ImportBatch.Status.VALIDATING

        batch.save(
            update_fields=["status"]
        )

        valid_rows = 0
        error_rows = 0

        # Validate each row.
        for row in batch.rows.order_by("row_number"):

            normalized_data, errors = handler.validate_row(
                row.raw_data
            )

            row.raw_data = normalized_data
            row.errors = errors

            if errors:
                row.status = ImportRow.Status.ERROR
                error_rows += 1
            else:
                row.status = ImportRow.Status.VALID
                valid_rows += 1

            row.save(
                update_fields=[
                    "raw_data",
                    "errors",
                    "status",
                ]
            )

        # Optional handler-level validation.
        #
        # This allows a future importer to validate rules that
        # depend on multiple rows.
        handler.validate_batch(
            batch.rows.all()
        )

        # Recalculate the persisted batch counts.
        batch.valid_rows = valid_rows
        batch.error_rows = error_rows

        if error_rows:
            batch.status = ImportBatch.Status.FAILED
        else:
            batch.status = ImportBatch.Status.VALIDATED

        batch.save(
            update_fields=[
                "valid_rows",
                "error_rows",
                "status",
            ]
        )

        # ---------------------------------------------------------
        # Activity logging
        # ---------------------------------------------------------
        #
        # We do not create one ActivityLog per row.
        #
        # Instead, one lifecycle event is recorded for the batch.
        #
        if error_rows:
            ImportBatchService._log_activity(
                batch=batch,
                action="REJECT",
                changes={
                    "event": "IMPORT_BATCH_VALIDATION_FAILED",
                    "status": batch.status,
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "error_rows": batch.error_rows,
                },
            )
        else:
            ImportBatchService._log_activity(
                batch=batch,
                action="UPDATE",
                changes={
                    "event": "IMPORT_BATCH_VALIDATED",
                    "status": batch.status,
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "error_rows": batch.error_rows,
                },
            )

        return batch

    @staticmethod
    @transaction.atomic
    def commit(batch):
        """
        Commit a previously validated batch.

        The batch row is locked and re-read inside the transaction so
        concurrent commit requests cannot both execute the destination
        handler.

        If the handler raises an exception:

        - destination writes are rolled back
        - batch remains uncommitted
        - committed_at is not set
        - row statuses are not changed
        - commit ActivityLog is rolled back
        """

        # ---------------------------------------------------------
        # Lock and re-read the batch inside the transaction.
        # ---------------------------------------------------------
        #
        # This is important for concurrent commit requests.
        #
        # Two requests may have received the same VALIDATED batch
        # object before entering this method. Therefore we must NOT
        # rely on the passed-in object's status.
        #
        locked_batch = (
            ImportBatch.objects
            .select_for_update()
            .get(pk=batch.pk)
        )

        # ---------------------------------------------------------
        # Check the current database state.
        # ---------------------------------------------------------

        if locked_batch.status == ImportBatch.Status.COMMITTED:
            raise ValidationError(
                "This batch has already been committed."
            )

        if locked_batch.status != ImportBatch.Status.VALIDATED:
            raise ValidationError(
                "Only a validated batch can be committed. "
                f"Current status: {locked_batch.status}."
            )

        # ---------------------------------------------------------
        # Get the concrete handler.
        # ---------------------------------------------------------
        #
        # If there is no registered handler, this fails safely.
        # Because the batch is inside the transaction, no commit
        # state is persisted.
        #

        handler = ImportHandlerRegistry.get_handler(
            locked_batch.import_type
        )

        # ---------------------------------------------------------
        # Destination-specific commit.
        # ---------------------------------------------------------
        #
        # The concrete importer owns destination writes.
        #

        handler.commit(locked_batch)

        # ---------------------------------------------------------
        # Mark batch as committed.
        # ---------------------------------------------------------

        locked_batch.status = ImportBatch.Status.COMMITTED

        locked_batch.committed_at = timezone.now()

        locked_batch.save(
            update_fields=[
                "status",
                "committed_at",
            ]
        )

        # ---------------------------------------------------------
        # Mark valid rows as committed.
        # ---------------------------------------------------------

        locked_batch.rows.filter(
            status=ImportRow.Status.VALID
        ).update(
            status=ImportRow.Status.COMMITTED
        )

        # ---------------------------------------------------------
        # Activity logging.
        # ---------------------------------------------------------

        ImportBatchService._log_activity(
            batch=locked_batch,
            action="APPROVE",
            changes={
                "event": "IMPORT_BATCH_COMMITTED",
                "status": locked_batch.status,
                "total_rows": locked_batch.total_rows,
                "valid_rows": locked_batch.valid_rows,
                "error_rows": locked_batch.error_rows,
                "committed_at": (
                    locked_batch.committed_at.isoformat()
                    if locked_batch.committed_at
                    else None
                ),
            },
        )

        return locked_batch

class ImportUploadService:
    """
    Service responsible for creating import batches from uploaded files.

    Upload performs only:

        file storage
        ↓
        spreadsheet parsing
        ↓
        ImportBatch creation
        ↓
        ImportRow creation

    Upload does NOT validate destination business data
    and does NOT commit destination business data.
    """

    @staticmethod
    def _log_activity(batch, action, changes=None):
        """
        Create an ActivityLog entry for the upload lifecycle event.

        We use the existing ActivityLog contract and represent
        the import-specific event inside the changes JSON.
        """

        request = get_current_request()

        user = None
        ip_address = None
        user_agent = ""
        request_path = ""

        if request is not None:
            if (
                getattr(request, "user", None)
                and request.user.is_authenticated
            ):
                user = request.user

            ip_address = request.META.get(
                "REMOTE_ADDR"
            )

            user_agent = request.META.get(
                "HTTP_USER_AGENT",
                "",
            )

            request_path = request.path

        ActivityLog.objects.create(
            user=user or batch.uploaded_by,
            action=action,
            model_name="ImportBatch",
            object_id=str(batch.pk),
            object_repr=str(batch),
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
        )

    @staticmethod
    def validate_module_code(module_code):
        """
        Validate the module code against the canonical
        Module Registry.

        Only enabled modules are accepted.

        If module_code is not supplied, None is returned.
        """

        if not module_code:
            return None

        module = Module.objects.filter(
            code=module_code,
            is_enabled=True,
        ).first()

        if not module:
            raise ValidationError(
                {
                    "module_code": (
                        f"Unknown or disabled module code: "
                        f"{module_code}"
                    )
                }
            )

        return module

    @staticmethod
    @transaction.atomic
    def create_batch(
        *,
        uploaded_file,
        uploaded_by,
        import_type,
        module_code=None,
        org_node=None,
        reporting_period=None,
    ):
        """
        Store the uploaded Excel file using Django storage,
        parse it, and create ImportBatch and ImportRow records.

        This method does NOT perform row validation.

        Lifecycle:

            File Upload
                ↓
            Parse XLSX
                ↓
            Create ImportBatch
                ↓
            Create ImportRows
                ↓
            UPLOADED

        Validation is performed separately by
        ImportBatchService.validate_batch().

        Commit is performed separately by
        ImportBatchService.commit().
        """

        # ---------------------------------------------------------
        # Validate module code
        # ---------------------------------------------------------

        ImportUploadService.validate_module_code(
            module_code
        )

        # ---------------------------------------------------------
        # Store uploaded file
        # ---------------------------------------------------------

        storage_path = default_storage.save(
            f"imports/{uploaded_file.name}",
            uploaded_file,
        )

        try:

            # -----------------------------------------------------
            # Open spreadsheet directly from Django storage
            # -----------------------------------------------------

            with default_storage.open(
                storage_path,
                "rb",
            ) as stored_file:

                parser = ExcelParser()

                # -------------------------------------------------
                # Create ImportBatch before creating ImportRows
                # -------------------------------------------------

                batch = ImportBatch.objects.create(
                    import_type=import_type,
                    file_name=uploaded_file.name,
                    file_path=storage_path,
                    uploaded_by=uploaded_by,
                    module_code=module_code,
                    org_node=org_node,
                    reporting_period=reporting_period,
                    status=ImportBatch.Status.UPLOADED,
                    total_rows=0,
                )

                # -------------------------------------------------
                # Parse rows incrementally
                # -------------------------------------------------

                rows_buffer = []
                total_rows = 0

                for row in parser.parse(stored_file):

                    rows_buffer.append(
                        ImportRow(
                            batch=batch,
                            row_number=row["row_number"],
                            raw_data=row["raw_data"],
                            status=ImportRow.Status.VALID,
                        )
                    )

                    total_rows += 1

                    # Insert rows in chunks of 1000
                    if len(rows_buffer) >= 1000:
                        ImportRow.objects.bulk_create(
                            rows_buffer
                        )
                        rows_buffer.clear()

                # -------------------------------------------------
                # Insert remaining rows
                # -------------------------------------------------

                if rows_buffer:
                    ImportRow.objects.bulk_create(
                        rows_buffer
                    )

                # -------------------------------------------------
                # Update total row count
                # -------------------------------------------------

                batch.total_rows = total_rows

                batch.save(
                    update_fields=["total_rows"]
                )

            # -----------------------------------------------------
            # Activity logging
            # -----------------------------------------------------

            ImportUploadService._log_activity(
                batch=batch,
                action="CREATE",
                changes={
                    "event": "IMPORT_BATCH_UPLOADED",
                    "import_type": batch.import_type,
                    "file_name": batch.file_name,
                    "total_rows": batch.total_rows,
                    "module_code": batch.module_code,
                    "status": batch.status,
                },
            )

            return batch

        except Exception:

            # -----------------------------------------------------
            # Cleanup uploaded file on failure
            # -----------------------------------------------------

            if default_storage.exists(storage_path):
                default_storage.delete(
                    storage_path
                )

            raise