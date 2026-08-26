from django.contrib import admin

from apps.data_capture.models import (
    DataRequest,
    DataRequestEvent,
    Submission,
    SubmissionEvent,
    Answer,
    AnswerTableRow,
    AnswerTableCell,
    EvidenceFile,
)


# Register your models here.

admin.site.register(DataRequest)
admin.site.register(DataRequestEvent)
admin.site.register(Submission)
admin.site.register(SubmissionEvent)
admin.site.register(Answer)
admin.site.register(AnswerTableRow)
admin.site.register(AnswerTableCell)
admin.site.register(EvidenceFile)