import pytest

from mikeio1d.pandas_extension import ResultFrameAggregator

import pandas as pd
import numpy as np


@pytest.fixture(params=["max", np.mean, ["max"]])
def agg(params):
    return params


class TestResultFrameAggregatorUnit:
    def test_init(self):
        with pytest.raises(ValueError):
            ResultFrameAggregator()

        ResultFrameAggregator("max")
        ResultFrameAggregator(np.mean)
        ResultFrameAggregator("max", chainage="min")
        ResultFrameAggregator("max", chainage="min", duplicate="first")
        ResultFrameAggregator(time="max")
        ResultFrameAggregator(time="max", chainage="first")

        with pytest.raises(ValueError):
            ResultFrameAggregator(["max"])

        with pytest.raises(ValueError):
            ResultFrameAggregator({"time": "max"})

    def test_init_agg_strategies(self):
        pass

    def test_validate(self):
        pass

    def test_validate_levels(self):
        pass

    def test_validate_agg_strategies(self):
        pass

    def test_validate_agg_strategy(self):
        pass

    def test_aggregate(self):
        pass

    def test_entity_levels(self):
        pass

    def test_agg_levels(self):
        pass

    def test_agg_strategies(self):
        pass

    def test_set_agg_strategy(self):
        pass

    def test_get_agg_strategy(self):
        pass

    def test_validate_df(self):
        pass

    def test_has_level_name(self):
        pass

    def test_remove_group_level(self):
        pass

    def test_aggregate_along_level(self):
        pass

    def test_aggregate_along_time(self):
        pass

    def test_finalize_df_post_aggregate(self):
        pass
