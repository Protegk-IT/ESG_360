from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook


class ImportFileError(Exception):
    """Raised when an import file cannot be parsed."""


class ExcelParser:
    """
    Generic XLSX parser.

    This parser knows nothing about Answers, Datapoints,
    Framework Nodes, Stakeholders, or Emission Factors.
    """

    SUPPORTED_EXTENSIONS = {".xlsx"}

    def parse(self, file_path):
        path = Path(file_path)

        self._validate_file(path)

        try:
            workbook = load_workbook(
                filename=path,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise ImportFileError(
                "The uploaded Excel file could not be read."
            ) from exc

        try:
            worksheet = workbook.active

            rows = list(
                worksheet.iter_rows(
                    values_only=True,
                )
            )

            if not rows:
                raise ImportFileError(
                    "The Excel file does not contain any rows."
                )

            headers = self._get_headers(rows[0])

            parsed_rows = []

            for excel_row_number, values in enumerate(
                rows[1:],
                start=2,
            ):
                if self._is_blank_row(values):
                    continue

                raw_data = {}

                for index, header in enumerate(headers):
                    value = values[index] if index < len(values) else None
                    raw_data[header] = self._json_safe(value)

                parsed_rows.append(
                    {
                        "row_number": excel_row_number,
                        "raw_data": raw_data,
                    }
                )

            return parsed_rows

        finally:
            workbook.close()

    @classmethod
    def _validate_file(cls, path):
        if not path.exists():
            raise ImportFileError(
                "The uploaded file could not be found."
            )

        if path.suffix.lower() not in cls.SUPPORTED_EXTENSIONS:
            raise ImportFileError(
                "Unsupported file type. Only .xlsx files are supported."
            )

    @staticmethod
    def _get_headers(header_row):
        headers = []

        for value in header_row:
            if value is None:
                headers.append("")
            else:
                headers.append(str(value).strip())

        while headers and headers[-1] == "":
            headers.pop()

        if not headers:
            raise ImportFileError(
                "The Excel file does not contain a header row."
            )

        if any(not header for header in headers):
            raise ImportFileError(
                "The Excel header row contains an empty column name."
            )

        if len(headers) != len(set(headers)):
            raise ImportFileError(
                "The Excel header row contains duplicate column names."
            )

        return headers

    @staticmethod
    def _is_blank_row(values):
        return all(
            value is None or str(value).strip() == ""
            for value in values
        )

    @staticmethod
    def _json_safe(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, bytes):
            return value.decode(
                "utf-8",
                errors="replace",
            )

        return value