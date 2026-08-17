from rest_framework import serializers

from .models import ImportBatch, ImportRow


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "import_type",
            "file_name",
            "file_path",
            "module_code",
            "status",
            "total_rows",
            "valid_rows",
            "error_rows",
            "uploaded_at",
            "committed_at",
        ]
        read_only_fields = fields

class ImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRow
        fields = [
            "id",
            "batch",
            "row_number",
            "raw_data",
            "status",
            "errors",
        ]
        read_only_fields = fields