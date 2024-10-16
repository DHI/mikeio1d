from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict
    from .result_reader import ResultReader

from ..various import NAME_DELIMITER

from .result_reader_copier import ResultReaderCopier
from .result_reader_query import ResultReaderQuery


class ResultReaderType:
    COPIER = "copier"
    QUERY = "query"


class ResultReaderCreator:
    @staticmethod
    def create(
        result_reader_type,
        res1d,
        file_path=None,
        lazy_load=False,
        header_load=False,
        reaches=None,
        nodes=None,
        catchments=None,
        col_name_delimiter=NAME_DELIMITER,
        put_chainage_in_col_name=True,
    ) -> ResultReader:
        reasult_readers: Dict[ResultReaderType, ResultReader] = {
            ResultReaderType.COPIER: ResultReaderCopier,
            ResultReaderType.QUERY: ResultReaderQuery,
        }

        reader = reasult_readers.get(result_reader_type, None)

        return reader(
            res1d,
            file_path,
            lazy_load,
            header_load,
            reaches,
            nodes,
            catchments,
            col_name_delimiter,
            put_chainage_in_col_name,
        )
