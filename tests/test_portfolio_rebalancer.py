import pytest

from portfolio_rebalancing import PortfolioRebalancer


def test_calculate_trades_includes_target_asset_without_holdings():
    rebalancer = PortfolioRebalancer({'AAA': 0.5, 'BBB': 0.5})
    positions = {
        'AAA': (10, 10.0),
        'BBB': (0.0, 10.0),
    }

    trades = rebalancer.calculate_trades(positions, cash=0.0)

    assert pytest.approx(trades['BBB'], rel=1e-6) == 5.0
    assert pytest.approx(trades['AAA'], rel=1e-6) == -5.0
