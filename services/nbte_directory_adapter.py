
"""
NBTE Academic Directory Adapter
-------------------------------

E2.4 adapter for the National Board for Technical Education (NBTE)
public Polytechnic directory.

Responsibilities:

1. Fetch the public NBTE Polytechnic directory.
2. Parse institution rows from the NBTE directory response.
3. Preserve the NBTE TVETCode as the external identifier.
4. Preserve NBTE institution display names and source metadata.
5. Optionally retrieve institution details from the official NBTE
   details endpoint.
6. Optionally retrieve approved programme information from the
   official NBTE programmes endpoint.
7. Convert institution information into the existing
   AcademicDirectorySourceRecord contract.
8. Preserve raw source information in source_snapshot.
9. Never create or modify database records.
10. Never infer SIWES participation.
11. Never modify SIWESConfiguration.
12. Never create DataSource or SourceEvidence records.

The adapter intentionally uses Python's standard-library HTMLParser.
No BeautifulSoup dependency is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlencode, urljoin

import requests

from services.academic_directory_import import (
    AcademicDirectorySourceRecord,
)


NBTE_DIRECTORY_URL = (
    "https://www.digitalnbte.nbte.gov.ng/Public/PUCPolytechnics"
)

NBTE_DETAILS_URL = (
    "https://www.digitalnbte.nbte.gov.ng/Public/PUCDetailsModal"
)

NBTE_PROGRAMMES_URL = (
    "https://www.digitalnbte.nbte.gov.ng/Public/PUCProgrammesModal"
)

NBTE_SOURCE_NAME = (
    "National Board for Technical Education"
)

NBTE_SOURCE_TYPE = (
    "National Technical Education Directory"
)

DEFAULT_TIMEOUT_SECONDS = 30


class NBTEAdapterError(ValueError):
    """Raised when an NBTE source record cannot be safely normalized."""


@dataclass(frozen=True)
class NBTEInstitutionRow:
    """
    Source-shaped NBTE institution directory row.
    """

    external_identifier: str
    external_name: str
    category: Optional[str] = None
    ownership: Optional[str] = None
    state: Optional[str] = None

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "external_identifier": self.external_identifier,
            "external_name": self.external_name,
            "category": self.category,
            "ownership": self.ownership,
            "state": self.state,
        }


@dataclass(frozen=True)
class NBTEInstitutionDetails:
    """
    Source-shaped NBTE institution details response.
    """

    external_identifier: str
    external_name: str
    ownership: Optional[str] = None
    category: Optional[str] = None
    official_website: Optional[str] = None
    state: Optional[str] = None
    lga: Optional[str] = None
    address: Optional[str] = None

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "external_identifier": self.external_identifier,
            "external_name": self.external_name,
            "ownership": self.ownership,
            "category": self.category,
            "official_website": self.official_website,
            "state": self.state,
            "lga": self.lga,
            "address": self.address,
        }


@dataclass(frozen=True)
class NBTEApprovedProgramme:
    """
    Source-shaped NBTE approved-programme record.

    This is recognition/accreditation information from NBTE.
    It is deliberately not a DSA SIWES configuration.
    """

    programme_name: str
    grant_date: Optional[str] = None
    expiry_date: Optional[str] = None
    accreditation_type: Optional[str] = None
    number_of_years: Optional[str] = None
    score: Optional[str] = None
    status: Optional[str] = None

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "programme_name": self.programme_name,
            "grant_date": self.grant_date,
            "expiry_date": self.expiry_date,
            "accreditation_type": self.accreditation_type,
            "number_of_years": self.number_of_years,
            "score": self.score,
            "status": self.status,
        }


class _HTMLNode:
    """
    Small dependency-free HTML node used by the adapter parser.
    """

    def __init__(
        self,
        tag: str,
        attrs: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children: List["_HTMLNode"] = []
        self.text_parts: List[str] = []

    def text(self) -> str:
        pieces = list(self.text_parts)

        for child in self.children:
            pieces.append(child.text())

        return " ".join(
            piece.strip()
            for piece in pieces
            if piece and piece.strip()
        ).strip()

    def find_all(self, tag: Optional[str] = None) -> List["_HTMLNode"]:
        found: List["_HTMLNode"] = []

        for child in self.children:
            if tag is None or child.tag == tag:
                found.append(child)

            found.extend(child.find_all(tag))

        return found


class _NBTEHTMLParser(HTMLParser):
    """
    Minimal dependency-free DOM builder.

    It is intentionally small and only supports the structures needed
    by the observed NBTE public responses.
    """

    VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True,
        )

        self.root = _HTMLNode("root")
        self.stack: List[_HTMLNode] = [self.root]

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        node = _HTMLNode(
            tag.lower(),
            {
                str(key): (
                    "" if value is None else str(value)
                )
                for key, value in attrs
            },
        )

        self.stack[-1].children.append(node)

        if tag.lower() not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(
        self,
        tag: str,
        attrs,
    ) -> None:
        node = _HTMLNode(
            tag.lower(),
            {
                str(key): (
                    "" if value is None else str(value)
                )
                for key, value in attrs
            },
        )

        self.stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        for index in range(
            len(self.stack) - 1,
            0,
            -1,
        ):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].text_parts.append(data)


def _parse_html(html: str) -> _HTMLNode:
    if html is None:
        raise NBTEAdapterError(
            "NBTE HTML response cannot be None."
        )

    if not isinstance(html, str):
        raise NBTEAdapterError(
            "NBTE HTML response must be a string."
        )

    if not html.strip():
        raise NBTEAdapterError(
            "NBTE HTML response cannot be empty."
        )

    parser = _NBTEHTMLParser()

    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise NBTEAdapterError(
            "NBTE HTML response could not be parsed."
        ) from exc

    return parser.root


class NBTEHTMLAdapter:
    """
    Helper namespace for dependency-free NBTE HTML extraction.
    """

    @staticmethod
    def _clean(value: Any) -> Optional[str]:
        if value is None:
            return None

        value = unescape(str(value)).strip()

        return value or None

    @classmethod
    def _required(
        cls,
        value: Any,
        field_name: str,
    ) -> str:
        cleaned = cls._clean(value)

        if not cleaned:
            raise NBTEAdapterError(
                f"NBTE record is missing {field_name}."
            )

        return cleaned

    @classmethod
    def parse_directory_rows(
        cls,
        html: str,
    ) -> List[NBTEInstitutionRow]:
        """
        Parse the institution table returned by PUCProcess.

        The observed NBTE response contains a header row followed by
        institution rows. The institution identifier is carried by
        the Details/ApprovedProgrammes button value, while the name
        is carried by a td id such as row100182.
        """

        root = _parse_html(html)

        records: List[NBTEInstitutionRow] = []

        tables = root.find_all("table")

        if not tables:
            raise NBTEAdapterError(
                "NBTE directory response contains no table."
            )

        institution_table = None

        for table in tables:
            headers = [
                node.text().strip().lower()
                for node in table.find_all("th")
            ]

            if (
                "institution name" in headers
                and "ownership" in headers
                and "state" in headers
            ):
                institution_table = table
                break

        if institution_table is None:
            raise NBTEAdapterError(
                "NBTE directory institution table was not found."
            )

        rows = institution_table.find_all("tr")

        for row_index, row in enumerate(
            rows,
            start=1,
        ):
            cells = row.find_all("td")

            if not cells:
                # Header or non-data row.
                continue

            buttons = row.find_all("button")

            identifier = None

            for button in buttons:
                button_id = (
                    button.attrs.get("id") or ""
                ).strip()

                value = cls._clean(
                    button.attrs.get("value")
                )

                if (
                    value
                    and button_id in {
                        "DetailsBtn",
                        "ApprovedProgrammesBtn",
                    }
                ):
                    identifier = value
                    break

            if identifier is None:
                # Do not guess an institution identifier from S/No.
                continue

            name = None

            for cell in cells:
                cell_id = (
                    cell.attrs.get("id") or ""
                ).strip()

                if cell_id == (
                    "row" + identifier
                ):
                    name = cell.text()
                    break

            if name is None and len(cells) >= 2:
                name = cells[1].text()

            name = cls._clean(name)

            if not name:
                raise NBTEAdapterError(
                    f"NBTE institution row {row_index} "
                    "has an identifier but no institution name."
                )

            values = [
                cls._clean(cell.text())
                for cell in cells
            ]

            category = (
                values[2]
                if len(values) > 2
                else None
            )

            ownership = (
                values[3]
                if len(values) > 3
                else None
            )

            state = (
                values[4]
                if len(values) > 4
                else None
            )

            records.append(
                NBTEInstitutionRow(
                    external_identifier=identifier,
                    external_name=name,
                    category=category,
                    ownership=ownership,
                    state=state,
                )
            )

        return records

    @classmethod
    def parse_details_html(
        cls,
        html: str,
        *,
        external_identifier: str,
    ) -> NBTEInstitutionDetails:
        """
        Parse the NBTE PUCDetailsModal response.
        """

        identifier = cls._required(
            external_identifier,
            "external_identifier",
        )

        root = _parse_html(html)

        pairs: Dict[str, str] = {}

        for row in root.find_all("tr"):
            headers = row.find_all("th")
            cells = row.find_all("td")

            if len(headers) != 1 or len(cells) != 1:
                continue

            key = cls._clean(headers[0].text())
            value = cls._clean(cells[0].text())

            if key:
                pairs[key.lower()] = value or ""

        name = cls._required(
            pairs.get("tvet name"),
            "TVET Name",
        )

        return NBTEInstitutionDetails(
            external_identifier=identifier,
            external_name=name,
            ownership=cls._clean(
                pairs.get("ownership")
            ),
            category=cls._clean(
                pairs.get("category")
            ),
            official_website=cls._clean(
                pairs.get("website")
            ),
            state=cls._clean(
                pairs.get("state")
            ),
            lga=cls._clean(
                pairs.get("lga")
            ),
            address=cls._clean(
                pairs.get("address")
            ),
        )

    @classmethod
    def parse_programmes_html(
        cls,
        html: str,
    ) -> List[NBTEApprovedProgramme]:
        """
        Parse the NBTE PUCProgrammesModal response.
        """

        root = _parse_html(html)

        programmes: List[NBTEApprovedProgramme] = []

        tables = root.find_all("table")

        programme_table = None

        for table in tables:
            headers = [
                node.text().strip().lower()
                for node in table.find_all("th")
            ]

            if (
                "programme" in headers
                and "grant date" in headers
                and "expiry date" in headers
                and "accreditation type" in headers
            ):
                programme_table = table
                break

        if programme_table is None:
            raise NBTEAdapterError(
                "NBTE approved-programme table was not found."
            )

        for row in programme_table.find_all("tr"):
            cells = row.find_all("td")

            if len(cells) < 7:
                continue

            values = [
                cls._clean(cell.text())
                for cell in cells
            ]

            programme_name = cls._clean(
                values[0]
            )

            if not programme_name:
                raise NBTEAdapterError(
                    "NBTE programme row has no programme name."
                )

            programmes.append(
                NBTEApprovedProgramme(
                    programme_name=programme_name,
                    grant_date=values[1],
                    expiry_date=values[2],
                    accreditation_type=values[3],
                    number_of_years=values[4],
                    score=values[5],
                    status=values[6],
                )
            )

        return programmes


class NBTEDirectoryAdapter:
    """
    Read-only adapter for the official NBTE Polytechnic directory.

    No SQLAlchemy dependency is used and no database mutation occurs.
    """

    source_name = NBTE_SOURCE_NAME
    source_type = NBTE_SOURCE_TYPE

    directory_url = NBTE_DIRECTORY_URL
    details_url = NBTE_DETAILS_URL
    programmes_url = NBTE_PROGRAMMES_URL

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
        return NBTEHTMLAdapter._clean(value)

    @classmethod
    def row_from_mapping(
        cls,
        row: Mapping[str, Any],
    ) -> NBTEInstitutionRow:
        """
        Normalize one NBTE institution mapping.

        This method performs no network or database access.
        """

        if not isinstance(row, Mapping):
            raise NBTEAdapterError(
                "NBTE institution row must be a mapping."
            )

        identifier = cls._clean(
            row.get("external_identifier")
            or row.get("TVETCode")
            or row.get("tvet_code")
            or row.get("value")
        )

        if not identifier:
            raise NBTEAdapterError(
                "NBTE institution record is missing TVETCode."
            )

        name = cls._clean(
            row.get("external_name")
            or row.get("TVETName")
            or row.get("tvet_name")
            or row.get("name")
        )

        if not name:
            raise NBTEAdapterError(
                "NBTE institution record is missing TVETName."
            )

        return NBTEInstitutionRow(
            external_identifier=identifier,
            external_name=name,
            category=cls._clean(
                row.get("category")
            ),
            ownership=cls._clean(
                row.get("ownership")
            ),
            state=cls._clean(
                row.get("state")
            ),
        )

    @classmethod
    def to_source_record(
        cls,
        row: NBTEInstitutionRow,
        *,
        details: Optional[NBTEInstitutionDetails] = None,
        reference_url: Optional[str] = None,
    ) -> AcademicDirectorySourceRecord:
        """
        Convert NBTE institution information into the common E2.1
        source-record contract.
        """

        if not isinstance(row, NBTEInstitutionRow):
            raise NBTEAdapterError(
                "Expected NBTEInstitutionRow."
            )

        if details is not None:
            if not isinstance(
                details,
                NBTEInstitutionDetails,
            ):
                raise NBTEAdapterError(
                    "Expected NBTEInstitutionDetails."
                )

            if (
                details.external_identifier
                != row.external_identifier
            ):
                raise NBTEAdapterError(
                    "NBTE row/details identifiers do not match."
                )

        external_name = (
            details.external_name
            if details is not None
            else row.external_name
        )

        ownership = (
            details.ownership
            if details is not None
            else row.ownership
        )

        state = (
            details.state
            if details is not None
            else row.state
        )

        website = (
            details.official_website
            if details is not None
            else None
        )

        snapshot: Dict[str, Any] = {
            "directory": row.to_snapshot(),
            "details": (
                details.to_snapshot()
                if details is not None
                else None
            ),
        }

        return AcademicDirectorySourceRecord(
            source_name=cls.source_name,
            source_type=cls.source_type,
            external_identifier=row.external_identifier,
            external_name=external_name,
            institution_type=ownership,
            city=None,
            state=state,
            official_website=website,
            reference_url=(
                reference_url
                or cls.directory_url
            ),
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
        Normalize NBTE institution mappings in deterministic order.
        """

        if rows is None:
            raise NBTEAdapterError(
                "NBTE institution record collection cannot be None."
            )

        records: List[
            AcademicDirectorySourceRecord
        ] = []

        for row in rows:
            normalized = cls.row_from_mapping(row)

            records.append(
                cls.to_source_record(
                    normalized,
                    reference_url=reference_url,
                )
            )

        return records

    def fetch_directory_html(self) -> str:
        """
        Fetch the public NBTE Polytechnic directory.

        The endpoint itself presents the category form. The actual
        institution table is returned by PUCProcess.
        """

        response = self.session.get(
            self.directory_url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text

    def fetch_polytechnic_directory_html(
        self,
    ) -> str:
        """
        Fetch all approved Polytechnic records using the observed
        NBTE PAll form submission.

        The endpoint requires the CategoryCode PAll.
        """

        response = self.session.get(
            self.directory_url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        html = response.text

        parser = _parse_html(html)

        csrf_token = None

        for node in parser.find_all("meta"):
            if (
                node.attrs.get("name", "").lower()
                == "csrf-token"
            ):
                csrf_token = self._clean(
                    node.attrs.get("content")
                )
                break

        if not csrf_token:
            raise NBTEAdapterError(
                "NBTE directory page did not provide a CSRF token."
            )

        process_url = urljoin(
            self.directory_url,
            "PUCProcess",
        )

        post_response = self.session.post(
            process_url,
            data={
                "_token": csrf_token,
                "CategoryCode": "PAll",
            },
            timeout=self.timeout,
        )

        post_response.raise_for_status()

        return post_response.text

    def fetch_institution_details_html(
        self,
        external_identifier: str,
    ) -> str:
        """
        Fetch one institution's official NBTE details response.
        """

        identifier = NBTEHTMLAdapter._required(
            external_identifier,
            "TVETCode",
        )

        response = self.session.get(
            self.details_url,
            params={
                "TVETCode": identifier,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text

    def fetch_approved_programmes_html(
        self,
        external_identifier: str,
        external_name: str,
    ) -> str:
        """
        Fetch one institution's approved-programme response.
        """

        identifier = NBTEHTMLAdapter._required(
            external_identifier,
            "TVETCode",
        )

        name = NBTEHTMLAdapter._required(
            external_name,
            "TVETName",
        )

        response = self.session.get(
            self.programmes_url,
            params={
                "TVETCode": identifier,
                "TVETName": name,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text

    @classmethod
    def parse_directory_html(
        cls,
        html: str,
        *,
        reference_url: Optional[str] = None,
    ) -> List[AcademicDirectorySourceRecord]:
        """
        Parse the complete NBTE PUCProcess response into the common
        source-record contract.
        """

        rows = NBTEHTMLAdapter.parse_directory_rows(
            html
        )

        return [
            cls.to_source_record(
                row,
                reference_url=(
                    reference_url
                    or cls.directory_url
                ),
            )
            for row in rows
        ]

    @classmethod
    def parse_details_html(
        cls,
        html: str,
        *,
        external_identifier: str,
    ) -> NBTEInstitutionDetails:
        return NBTEHTMLAdapter.parse_details_html(
            html,
            external_identifier=external_identifier,
        )

    @classmethod
    def parse_programmes_html(
        cls,
        html: str,
    ) -> List[NBTEApprovedProgramme]:
        return NBTEHTMLAdapter.parse_programmes_html(
            html
        )
