from django.apps import AppConfig


class ImportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.imports"

    def ready(self):
        from apps.imports.handlers import ImportHandlerRegistry
        from apps.imports.models import ImportBatch
        from apps.imports.answers import AnswersImportHandler

        ImportHandlerRegistry.register(
            ImportBatch.ImportType.ANSWERS,
            AnswersImportHandler,
        )