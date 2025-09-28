from datetime import datetime, timedelta

import pandas as pd

from services.data_service import DataService


def test_in_memory_cache_respects_ttl():
    service = DataService()
    fixed_now = datetime(2024, 1, 1, 10, 0, 0)
    service._now = lambda: fixed_now

    key = "cache-key"
    df = pd.DataFrame({"Close": [1, 2, 3]})

    service._set_cached_data(key, df)
    assert service._get_cached_data(key) is df

    service._now = lambda: fixed_now + timedelta(seconds=service.cache_ttl + 1)

    assert service._get_cached_data(key) is None
    assert key not in service._cache
