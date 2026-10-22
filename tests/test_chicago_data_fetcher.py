"""Regression coverage for the paginated homicide API used on cold starts."""
from unittest.mock import Mock, patch

import pytest
import requests

from chicago_data_fetcher import ChicagoHomicideDataFetcher


def csv_response(text):
    return Mock(text=text)


def test_fetches_distinct_pages_then_reuses_cache(tmp_path):
    fetcher = ChicagoHomicideDataFetcher(str(tmp_path))
    fetcher.batch_size = 2
    count = Mock()
    count.json.return_value = [{"count": "3"}]
    with patch("chicago_data_fetcher.requests.get", side_effect=[
        count,
        csv_response("id,year\n1,2024\n2,2024\n"),
        csv_response("id,year\n3,2025\n"),
    ]) as get, patch("time.sleep"):
        result = fetcher.fetch_all_data()
        assert result["id"].tolist() == [1, 2, 3]
        assert get.call_count == 3
        assert "/resource/iyvd-p5ga.json" in get.call_args_list[0].args[0]
        pages = get.call_args_list[1:]
        assert all(call.args[0].endswith("/resource/iyvd-p5ga.csv") for call in pages)
        assert [call.kwargs["params"]["$offset"] for call in pages] == [0, 2]
        assert all(call.kwargs["params"]["$order"] == "id" for call in pages)
        assert fetcher.fetch_all_data()["id"].tolist() == [1, 2, 3]
        assert get.call_count == 3


def test_rejects_endpoint_that_ignores_pagination(tmp_path):
    fetcher = ChicagoHomicideDataFetcher(str(tmp_path))
    with patch("chicago_data_fetcher.requests.get", return_value=csv_response("id\n1\n2\n3\n")):
        with pytest.raises(ValueError, match="ignored the requested page limit"):
            fetcher.fetch_batch(0, 2)


def test_failed_later_page_does_not_cache_partial_results(tmp_path):
    fetcher = ChicagoHomicideDataFetcher(str(tmp_path))
    fetcher.batch_size = 2
    count = Mock()
    count.json.return_value = [{"count": "3"}]
    with patch("chicago_data_fetcher.requests.get", side_effect=[
        count,
        csv_response("id,year\n1,2024\n2,2024\n"),
        requests.Timeout("city API unavailable"),
    ]), patch("time.sleep"):
        with pytest.raises(requests.Timeout):
            fetcher.fetch_all_data()
    assert not fetcher.cache_file.exists()
