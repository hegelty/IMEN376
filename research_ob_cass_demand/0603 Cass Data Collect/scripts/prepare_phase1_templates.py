from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


TEMPLATES = {
    "phase1_sku_demand_template.csv": [
        "date",
        "sku",
        "region",
        "channel",
        "actual_demand_kl",
        "shipments_kl",
        "sell_out_kl",
        "stockout_flag",
        "source_system",
    ],
    "phase1_inventory_template.csv": [
        "date",
        "sku",
        "dc_id",
        "region",
        "inventory_on_hand_kl",
        "safety_stock_kl",
        "inbound_qty_kl",
        "outbound_qty_kl",
        "source_system",
    ],
    "phase1_tank_state_template.csv": [
        "date",
        "tank_id",
        "sku",
        "fermentation_start_date",
        "planned_release_date",
        "tank_capacity_kl",
        "current_status",
        "batch_id",
        "source_system",
    ],
    "phase1_promotion_calendar_template.csv": [
        "date",
        "sku",
        "region",
        "channel",
        "promotion_flag",
        "promotion_type",
        "discount_pct",
        "expected_uplift_pct",
        "source_system",
    ],
    "phase1_account_order_template.csv": [
        "date",
        "account_id",
        "sku",
        "region",
        "channel",
        "recommended_order_kl",
        "actual_order_kl",
        "sales_override_flag",
        "source_system",
    ],
}


REQUIREMENTS = [
    {
        "requirement_id": "P1-DATA-1",
        "dataset": "phase1_sku_demand_template.csv",
        "required_for": "actual SKU-level forecast target",
        "minimum_grain": "daily SKU x region/channel",
        "status_without_file": "BLOCKS_PHASE_1",
    },
    {
        "requirement_id": "P1-DATA-2",
        "dataset": "phase1_inventory_template.csv",
        "required_for": "DC safety stock recommendation",
        "minimum_grain": "daily SKU x DC",
        "status_without_file": "PROXY_ONLY",
    },
    {
        "requirement_id": "P1-DATA-3",
        "dataset": "phase1_tank_state_template.csv",
        "required_for": "fermentation tank allocation",
        "minimum_grain": "daily tank/batch state",
        "status_without_file": "PROXY_ONLY",
    },
    {
        "requirement_id": "P1-DATA-4",
        "dataset": "phase1_promotion_calendar_template.csv",
        "required_for": "promotion-aware covariate forecast",
        "minimum_grain": "daily SKU x region/channel",
        "status_without_file": "COVARIATE_MISSING",
    },
    {
        "requirement_id": "P1-DATA-5",
        "dataset": "phase1_account_order_template.csv",
        "required_for": "wholesaler/account advisory order",
        "minimum_grain": "daily account x SKU",
        "status_without_file": "PROXY_ONLY",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Phase 1 internal-data CSV templates.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing template files. By default existing files are preserved.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    created = []
    skipped = []
    for filename, columns in TEMPLATES.items():
        path = DATA_DIR / filename
        if path.exists() and not args.overwrite:
            skipped.append(filename)
            continue
        pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")
        created.append(filename)
    pd.DataFrame(REQUIREMENTS).to_csv(
        DATA_DIR / "phase1_data_requirements.csv", index=False, encoding="utf-8-sig"
    )
    print(f"Created/updated {len(created)} Phase 1 templates and requirements to {DATA_DIR}")
    if skipped:
        print(f"Preserved existing templates: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
