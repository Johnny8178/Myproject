from pprint import pprint

from trade_automation import AutomationConfig, OrderRequest, TradeAutomationService


def main():
    config = AutomationConfig.from_env()
    service = TradeAutomationService(config=config)
    order = OrderRequest(
        action="BUY",
        symbol="600000",
        price=10.50,
        quantity=100,
        dry_run=config.default_dry_run,
        note="safe demo order",
    )
    result = service.execute(order)
    pprint(result.__dict__)


if __name__ == "__main__":
    main()
