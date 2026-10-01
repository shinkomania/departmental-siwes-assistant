"""
NUC Academic Directory Adapter
------------------------------

E2.3 adapter for the Nigerian Universities Commission (NUC)
academic-directory source.

Responsibilities:

1. Fetch the public NUC university directory.
2. Parse institution rows from the NUC directory table.
3. Convert each valid row into an AcademicDirectorySourceRecord.
4. Preserve the NUC source identity and raw row information.
5. Preserve the NUC reference URL.
6. Never create or modify database records.
7. Never infer SIWES participation.
8. Never create DataSource or SourceEvidence records.
9. Never create or modify Institution, AcademicUnit, Department,
   Programme, or SIWESConfiguration records.

Live fetching is intentionally separate from publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Iterable, List, Mapping, Optional

import requests

from services.academic_directory_import import (
    AcademicDirectorySourceRecord,
)


NUC_DIRECTORY_URL = "https://enuc.nuc.edu.ng/nus"

NUC_SOURCE_NAME = "Nigerian Universities Commission"

NUC_SOURCE_TYPE = "National Academic Directory"

DEFAULT_TIMEOUT_SECONDS = 30


class NUCAdapterError(ValueError):
    """Raised when a NUC source record cannot be safely normalized."""


@dataclass(frozen=True)
class NUCInstitutionRow:
    """
    Raw institution row extracted from the NUC directory.

    This is deliberately source-shaped rather than a canonical DSA model.
    """

    external_identifier: str
    external_name: str
    ownership: Optional[str] = None
    state: Optional[str] = None
    official_website: Optional[str] = None
    year_established: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    vice_chancellor: Optional[str] = None

    def to_snapshot(self) -> dict:
        return {
            "external_identifier": self.external_identifier,
            "external_name": self.external_name,
            "ownership": self.ownership,
            "state": self.state,
            "official_website": self.official_website,
            "year_established": self.year_established,
            "email": self.email,
            "phone": self.phone,
            "vice_chancellor": self.vice_chancellor,
        }


class _NUCButton:
    """
    Minimal button object exposing the attributes required by
    parse_html_rows().
    """

    def __init__(self, attrs):
        self.attrs = dict(attrs)


class _NUCHTMLRow:
    """
    Minimal HTML-row object exposing the subset of the
    BeautifulSoup-style interface required by the adapter.
    """

    def __init__(self, attrs):
        self.attrs = dict(attrs)
        self._buttons = []

    def add_button(self, button):
        self._buttons.append(button)

    def find(self, tag, class_=None):
        if tag != "button":
            return None

        for button in self._buttons:
            if class_ is None:
                return button

            classes = str(
                button.attrs.get("class", "")
            ).split()

            if class_ in classes:
                return button

        return None


class _NUCHTMLParser(HTMLParser):
    """
    Dependency-free parser for the live NUC universitiesTable.

    Only the table identified by universitiesTable is captured.
    Institution metadata is carried by button.view-details.
    """

    def __init__(self):
        super().__init__(
            convert_charrefs=True,
        )

        self.in_target_table = False
        self.table_depth = 0

        self.current_row = None
        self.current_button = None

        self.rows = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)

        if tag == "table":
            if attrs_dict.get("id") == "universitiesTable":
                self.in_target_table = True
                self.table_depth = 1
            elif self.in_target_table:
                self.table_depth += 1

            return

        if not self.in_target_table:
            return

        if tag == "tr":
            self.current_row = _NUCHTMLRow(
                attrs_dict
            )
            return

        if (
            tag == "button"
            and self.current_row is not None
        ):
            classes = str(
                attrs_dict.get("class", "")
            ).split()

            if "view-details" in classes:
                self.current_button = _NUCButton(
                    attrs_dict
                )

    def handle_endtag(self, tag):
        tag = tag.lower()

        if not self.in_target_table:
            return

        if (
            tag == "button"
            and self.current_button is not None
        ):
            if self.current_row is not None:
                self.current_row.add_button(
                    self.current_button
                )

            self.current_button = None
            return

        if tag == "tr":
            if self.current_row is not None:
                self.rows.append(
                    self.current_row
                )

            self.current_row = None
            self.current_button = None
            return

        if tag == "table":
            if self.table_depth > 0:
                self.table_depth -= 1

            if self.table_depth == 0:
                self.in_target_table = False

    def error(self, message):
        raise NUCAdapterError(
            f"Unable to parse NUC HTML: {message}"
        )



class NUCDirectoryAdapter:
    """
    Read-only adapter for the NUC university directory.

    The adapter has no SQLAlchemy dependency and performs no database
    mutation.
    """

    source_name = NUC_SOURCE_NAME
    source_type = NUC_SOURCE_TYPE
    directory_url = NUC_DIRECTORY_URL

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    @staticmethod
    def _clean(value: Any) -> Optional[str]:
        if value is None:
            return None

        value = str(value).strip()

        return value or None

    @classmethod
    def _require_name(cls, value: Any) -> str:
        cleaned = cls._clean(value)

        if not cleaned:
            raise NUCAdapterError(
                "NUC institution record is missing external_name."
            )

        return cleaned

    @classmethod
    def _require_identifier(cls, value: Any) -> str:
        cleaned = cls._clean(value)

        if not cleaned:
            raise NUCAdapterError(
                "NUC institution record is missing external_identifier."
            )

        return cleaned

    @classmethod
    def row_from_mapping(
        cls,
        row: Mapping[str, Any],
    ) -> NUCInstitutionRow:
        """
        Normalize one source-shaped mapping.

        This method does not perform network access or database access.
        """

        if not isinstance(row, Mapping):
            raise NUCAdapterError(
                "NUC institution row must be a mapping."
            )

        external_identifier = cls._require_identifier(
            row.get("external_identifier")
            or row.get("data-id")
            or row.get("id")
        )

        external_name = cls._require_name(
            row.get("external_name")
            or row.get("data-name")
            or row.get("name")
        )

        return NUCInstitutionRow(
            external_identifier=external_identifier,
            external_name=external_name,
            ownership=cls._clean(
                row.get("ownership")
                or row.get("data-ownership")
            ),
            state=cls._clean(
                row.get("state")
                or row.get("data-state")
            ),
            official_website=cls._clean(
                row.get("official_website")
                or row.get("data-website")
                or row.get("website")
            ),
            year_established=cls._clean(
                row.get("year_established")
                or row.get("data-year")
                or row.get("year")
            ),
            email=cls._clean(
                row.get("email")
                or row.get("data-email")
            ),
            phone=cls._clean(
                row.get("phone")
                or row.get("data-phone")
            ),
            vice_chancellor=cls._clean(
                row.get("vice_chancellor")
                or row.get("data-vc")
            ),
        )

    @classmethod
    def to_source_record(
        cls,
        row: NUCInstitutionRow,
        *,
        reference_url: Optional[str] = None,
    ) -> AcademicDirectorySourceRecord:
        """
        Convert a normalized NUC row into the E2.1 source-record contract.
        """

        if not isinstance(row, NUCInstitutionRow):
            raise NUCAdapterError(
                "Expected NUCInstitutionRow."
            )

        snapshot = row.to_snapshot()

        return AcademicDirectorySourceRecord(
            source_name=cls.source_name,
            source_type=cls.source_type,
            external_identifier=row.external_identifier,
            external_name=row.external_name,
            institution_type=row.ownership,
            city=None,
            state=row.state,
            official_website=row.official_website,
            reference_url=reference_url or cls.directory_url,
            source_snapshot=snapshot,
        )

    @classmethod
    def normalize_rows(
        cls,
        rows: Iterable[Mapping[str, Any]],
        *,
        reference_url: Optional[str] = None,
    ) -> List[AcademicDirectorySourceRecord]:
        """
        Normalize an iterable of NUC institution mappings.

        Order is preserved and no record is silently discarded.
        Malformed records raise NUCAdapterError.
        """

        if rows is None:
            raise NUCAdapterError(
                "NUC institution record collection cannot be None."
            )

        records: List[AcademicDirectorySourceRecord] = []

        for row in rows:
            normalized = cls.row_from_mapping(row)

            records.append(
                cls.to_source_record(
                    normalized,
                    reference_url=reference_url,
                )
            )

        return records

    @staticmethod
    def _extract_attributes_from_html_row(
        row: Any,
    ) -> Mapping[str, Any]:
        """
        Extract the NUC data-* attributes from one HTML table row.

        This method intentionally accepts a BeautifulSoup-like row object
        without requiring BeautifulSoup as a project dependency.
        """

        attrs = getattr(row, "attrs", None)

        if not isinstance(attrs, Mapping):
            raise NUCAdapterError(
                "NUC HTML row does not expose an attributes mapping."
            )

        return {
            "external_identifier": attrs.get("data-id"),
            "external_name": attrs.get("data-name"),
            "ownership": attrs.get("data-ownership"),
            "state": attrs.get("data-state"),
            "official_website": attrs.get("data-website"),
            "year_established": attrs.get("data-year"),
            "email": attrs.get("data-email"),
            "phone": attrs.get("data-phone"),
            "vice_chancellor": attrs.get("data-vc"),
        }

    @classmethod
    @staticmethod
    def parse_html_rows(
        rows,
        reference_url=None,
    ):
        """
        Convert NUC HTML table rows into
        AcademicDirectorySourceRecord objects.

        The live NUC directory stores institution metadata on the
        ``button.view-details`` element inside each table row rather
        than directly on the ``<tr>`` element.

        Required source attributes:
            data-id
            data-name

        Optional source attributes are preserved in source_snapshot.
        """

        if rows is None:
            raise NUCAdapterError(
                "NUC HTML row collection cannot be None."
            )

        records = []

        for row_index, row in enumerate(rows, start=1):
            if row is None:
                raise NUCAdapterError(
                    f"NUC HTML row {row_index} is invalid."
                )

            attrs = getattr(row, "attrs", None)

            if not isinstance(attrs, dict):
                raise NUCAdapterError(
                    f"NUC HTML row {row_index} has no attributes."
                )

            # Support the controlled fixture contract where the
            # metadata is already represented directly on the row.
            source_attrs = dict(attrs)

            # Live NUC rows place the source metadata on the
            # view-details button. BeautifulSoup-style rows expose
            # descendants through find()/find_all().
            button = None

            finder = getattr(row, "find", None)

            if callable(finder):
                try:
                    button = finder(
                        "button",
                        class_="view-details",
                    )
                except TypeError:
                    button = None

            # The NUC table contains non-institution rows such as
            # the table header. A row with neither direct institution
            # metadata nor a view-details button is therefore ignored.
            #
            # This does NOT weaken validation for actual institution
            # rows. Once a row contains institution metadata or a
            # view-details button, required fields remain mandatory.
            if (
                not source_attrs.get("data-id")
                and not source_attrs.get("data-name")
                and button is None
            ):
                continue

            if button is not None:
                button_attrs = getattr(
                    button,
                    "attrs",
                    None,
                )

                if isinstance(button_attrs, dict):
                    source_attrs.update(button_attrs)

            external_identifier = (
                source_attrs.get("data-id")
            )

            external_name = (
                source_attrs.get("data-name")
            )

            if external_identifier is None:
                raise NUCAdapterError(
                    "NUC institution record is missing "
                    "external_identifier/data-id."
                )

            external_identifier = str(
                external_identifier
            ).strip()

            if not external_identifier:
                raise NUCAdapterError(
                    "NUC institution record has an empty data-id."
                )

            if external_name is None:
                raise NUCAdapterError(
                    "NUC institution record is missing "
                    "external_name."
                )

            external_name = str(
                external_name
            ).strip()

            if not external_name:
                raise NUCAdapterError(
                    "NUC institution record has an empty "
                    "data-name."
                )

            def clean(value):
                if value is None:
                    return None

                value = str(value).strip()

                return value or None

            ownership = clean(
                source_attrs.get("data-ownership")
            )

            state = clean(
                source_attrs.get("data-state")
            )

            website = clean(
                source_attrs.get("data-website")
            )

            year = clean(
                source_attrs.get("data-year")
            )

            email = clean(
                source_attrs.get("data-email")
            )

            phone = clean(
                source_attrs.get("data-phone")
            )

            vice_chancellor = clean(
                source_attrs.get("data-vc")
            )

            snapshot = {
                "external_identifier": external_identifier,
                "external_name": external_name,
                "ownership": ownership,
                "state": state,
                "official_website": website,
                "year_established": year,
                "email": email,
                "phone": phone,
                "vice_chancellor": vice_chancellor,
            }

            records.append(
                AcademicDirectorySourceRecord(
                    source_name=NUCDirectoryAdapter.source_name,
                    source_type=NUCDirectoryAdapter.source_type,
                    external_identifier=external_identifier,
                    external_name=external_name,
                    institution_type=ownership,
                    city=None,
                    state=state,
                    official_website=website,
                    reference_url=(
                        reference_url
                        or NUCDirectoryAdapter.directory_url
                    ),
                    source_snapshot=snapshot,
                )
            )

        return records

    @classmethod
    def parse_directory_html(
        cls,
        html: str,
        *,
        reference_url: Optional[str] = None,
    ) -> List[AcademicDirectorySourceRecord]:
        """
        Parse live NUC directory HTML into source records.

        This method uses only Python's standard-library HTMLParser.
        It does not require BeautifulSoup and performs no database
        operation.

        The NUC directory contains one header row followed by
        institution rows. Institution metadata is stored on the
        button.view-details element inside each row.

        Rows without a view-details button are treated as
        non-institution rows and ignored. Actual institution rows
        remain strictly validated by parse_html_rows().
        """

        if html is None:
            raise NUCAdapterError(
                "NUC directory HTML cannot be None."
            )

        if not isinstance(html, str):
            raise NUCAdapterError(
                "NUC directory HTML must be a string."
            )

        if not html.strip():
            raise NUCAdapterError(
                "NUC directory HTML cannot be empty."
            )

        parser = _NUCHTMLParser()

        try:
            parser.feed(html)
            parser.close()
        except NUCAdapterError:
            raise
        except Exception as exc:
            raise NUCAdapterError(
                "Unable to parse NUC directory HTML."
            ) from exc

        rows = [
            row
            for row in parser.rows
            if row.find(
                "button",
                class_="view-details",
            ) is not None
        ]

        if not rows:
            raise NUCAdapterError(
                "NUC directory contains no institution rows."
            )

        return cls.parse_html_rows(
            rows,
            reference_url=(
                reference_url
                or cls.directory_url
            ),
        )

    def fetch_directory_html(self) -> str:
        """
        Fetch the live NUC directory HTML.

        No database operation occurs here.
        """

        response = self.session.get(
            self.directory_url,
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/153.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )

        response.raise_for_status()

        if not response.text.strip():
            raise NUCAdapterError(
                "NUC directory returned an empty response."
            )

        return response.text