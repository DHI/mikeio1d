"""Module for ResultReaderCreator class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict
    from .result_reader import ResultReader
    from ..filter import ResultFilter

from ..various import NAME_DELIMITER

from .result_reader_copier import ResultReaderCopier
from .result_reader_query import ResultReaderQuery


class ResultReaderType:
    """Enum class for ResultReader types."""

    COPIER = "copier"
    QUERY = "query"


class ResultReaderCreator:
    """Class for creating ResultReader objects."""

    @staticmethod
    def create(
        result_reader_type,
        res1d,
        file_path=None,
        col_name_delimiter=NAME_DELIMITER,
        put_chainage_in_col_name=True,
        filter: ResultFilter = None,
    ) -> ResultReader:
        """Create a ResultReader object based on the provided type."""
        reasult_readers: Dict[ResultReaderType, ResultReader] = {
            ResultReaderType.COPIER: ResultReaderCopier,
            ResultReaderType.QUERY: ResultReaderQuery,
        }

        reader = reasult_readers.get(result_reader_type, None)

        return reader(
            res1d=res1d,
            file_path=file_path,
            col_name_delimiter=col_name_delimiter,
            put_chainage_in_col_name=put_chainage_in_col_name,
            filter=filter,
        )
