"""Transactional evidence operations backed by Django storage."""

import os
import zipfile

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.data_capture.models import EvidenceFile, SubmissionStatus


class EvidenceService:
    """The only supported M5 path for evidence upload and removal."""

    @staticmethod
    def _detected_content_type(uploaded_file):
        """Identify supported formats from server-read bytes, not request MIME."""

        position = uploaded_file.tell()
        try:
            header = uploaded_file.read(16)
            uploaded_file.seek(0)
            if header.startswith(b"%PDF-"):
                return "application/pdf"
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return "image/png"
            if header.startswith(b"\xff\xd8\xff"):
                return "image/jpeg"
            if header.startswith(b"PK\x03\x04"):
                try:
                    with zipfile.ZipFile(uploaded_file) as archive:
                        names = set(archive.namelist())
                    if "[Content_Types].xml" in names and any(name.startswith("xl/") for name in names):
                        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                except zipfile.BadZipFile:
                    pass
            # CSV is the only accepted plain-text format. Require UTF-8 text
            # and at least one comma/newline so arbitrary text is not accepted.
            uploaded_file.seek(0)
            sample = uploaded_file.read(8192)
            try:
                text = sample.decode("utf-8")
            except UnicodeDecodeError:
                return None
            if "," in text or "\n" in text or "\r" in text:
                return "text/csv"
            return None
        finally:
            uploaded_file.seek(position)

    @classmethod
    @transaction.atomic
    def upload(cls, submission, *, actor, uploaded_file, answer=None):
        """Store validated evidence while the assigned maker's draft is editable."""

        from apps.data_capture.services.lifecycle import DataCaptureLifecycleService

        submission = DataCaptureLifecycleService._locked_submission(submission)
        DataCaptureLifecycleService._ensure_period_open(submission.data_request)
        DataCaptureLifecycleService._ensure_maker(submission, actor)
        if submission.status != SubmissionStatus.DRAFT:
            raise ValidationError("Evidence may only be changed while the submission is a draft.")
        if answer is not None and answer.submission_id != submission.id:
            raise ValidationError({"answer": "Evidence answer must belong to the selected submission."})

        if uploaded_file.size > EvidenceFile.MAX_FILE_SIZE:
            raise ValidationError({"file": "Evidence files must not exceed 10 MB."})
        content_type = cls._detected_content_type(uploaded_file)
        if content_type not in EvidenceFile.ALLOWED_CONTENT_TYPES:
            raise ValidationError({"file": "Unsupported evidence file type."})

        evidence = EvidenceFile(
            submission=submission,
            answer=answer,
            file=uploaded_file,
            original_filename=os.path.basename(uploaded_file.name)[:255],
            content_type=content_type,
            size=uploaded_file.size,
            uploaded_by=actor,
        )
        try:
            evidence.save()
        except Exception:
            # FileField writes to storage before the database row exists. Do
            # not leave a file behind when model/audit persistence rejects it.
            if evidence.file and evidence.file.name:
                evidence.file.storage.delete(evidence.file.name)
            raise
        return evidence

    @staticmethod
    @transaction.atomic
    def delete(evidence, *, actor):
        """Delete a draft-only evidence record and its storage object on commit."""

        from apps.data_capture.services.lifecycle import DataCaptureLifecycleService

        # Keep the submission-first lock order used by submit/review writes.
        # This prevents a draft evidence delete racing a concurrent submit.
        evidence_id = evidence.pk
        submission = DataCaptureLifecycleService._locked_submission(evidence.submission)
        evidence = EvidenceFile.objects.select_for_update().select_related("submission").get(pk=evidence_id)
        if evidence.submission_id != submission.id:
            raise ValidationError("Evidence does not belong to this submission.")
        DataCaptureLifecycleService._ensure_period_open(submission.data_request)
        DataCaptureLifecycleService._ensure_maker(submission, actor)
        if submission.status != SubmissionStatus.DRAFT:
            raise ValidationError("Evidence may only be deleted from an editable draft submission.")

        evidence._allow_service_delete = True
        try:
            evidence.delete()
        finally:
            del evidence._allow_service_delete
