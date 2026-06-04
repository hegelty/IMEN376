from __future__ import annotations

from pathlib import Path

import pandas as pd

from prepare_phase1_templates import DATA_DIR, ROOT


OUTPUT_DIR = ROOT / "model_outputs"


def read_template(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def normalize_keys(df: pd.DataFrame, required_keys: list[str]) -> pd.DataFrame:
    out = df.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
    for key in required_keys:
        if key in out.columns:
            out[key] = out[key].astype(str).str.strip()
    return out


def build_inventory_features() -> pd.DataFrame:
    inv = read_template("phase1_inventory_template.csv")
    if inv.empty:
        return pd.DataFrame(columns=["date", "sku", "region"])
    inv = normalize_keys(inv, ["sku", "region", "dc_id"])
    for col in ["inventory_on_hand_kl", "safety_stock_kl", "inbound_qty_kl", "outbound_qty_kl"]:
        inv[col] = pd.to_numeric(inv[col], errors="coerce")
    return (
        inv.groupby(["date", "sku", "region"], dropna=False)
        .agg(
            inventory_on_hand_kl=("inventory_on_hand_kl", "sum"),
            safety_stock_kl=("safety_stock_kl", "sum"),
            inbound_qty_kl=("inbound_qty_kl", "sum"),
            outbound_qty_kl=("outbound_qty_kl", "sum"),
            dc_count=("dc_id", "nunique"),
        )
        .reset_index()
    )


def build_promotion_features() -> pd.DataFrame:
    promo = read_template("phase1_promotion_calendar_template.csv")
    if promo.empty:
        return pd.DataFrame(columns=["date", "sku", "region", "channel"])
    promo = normalize_keys(promo, ["sku", "region", "channel"])
    promo["promotion_flag"] = pd.to_numeric(promo["promotion_flag"], errors="coerce").fillna(0)
    promo["discount_pct"] = pd.to_numeric(promo["discount_pct"], errors="coerce")
    promo["expected_uplift_pct"] = pd.to_numeric(promo["expected_uplift_pct"], errors="coerce")
    return (
        promo.groupby(["date", "sku", "region", "channel"], dropna=False)
        .agg(
            promotion_flag=("promotion_flag", "max"),
            discount_pct=("discount_pct", "max"),
            expected_uplift_pct=("expected_uplift_pct", "max"),
            promotion_type_count=("promotion_type", "nunique"),
        )
        .reset_index()
    )


def build_account_features() -> pd.DataFrame:
    account = read_template("phase1_account_order_template.csv")
    if account.empty:
        return pd.DataFrame(columns=["date", "sku", "region", "channel"])
    account = normalize_keys(account, ["account_id", "sku", "region", "channel"])
    for col in ["recommended_order_kl", "actual_order_kl", "sales_override_flag"]:
        account[col] = pd.to_numeric(account[col], errors="coerce")
    return (
        account.groupby(["date", "sku", "region", "channel"], dropna=False)
        .agg(
            account_count=("account_id", "nunique"),
            recommended_order_kl=("recommended_order_kl", "sum"),
            actual_order_kl=("actual_order_kl", "sum"),
            sales_override_count=("sales_override_flag", "sum"),
        )
        .reset_index()
    )


def build_tank_features() -> pd.DataFrame:
    tank = read_template("phase1_tank_state_template.csv")
    if tank.empty:
        return pd.DataFrame(columns=["date", "sku"])
    tank = normalize_keys(tank, ["tank_id", "sku", "batch_id", "current_status"])
    tank["tank_capacity_kl"] = pd.to_numeric(tank["tank_capacity_kl"], errors="coerce")
    tank["planned_release_date"] = pd.to_datetime(tank["planned_release_date"], errors="coerce")
    return (
        tank.groupby(["date", "sku"], dropna=False)
        .agg(
            active_tank_count=("tank_id", "nunique"),
            tank_capacity_kl=("tank_capacity_kl", "sum"),
            batch_count=("batch_id", "nunique"),
            planned_release_count=("planned_release_date", "count"),
        )
        .reset_index()
    )


def build_phase1_model_input() -> tuple[pd.DataFrame, pd.DataFrame]:
    demand = read_template("phase1_sku_demand_template.csv")
    status_rows = []

    if demand.empty:
        status_rows.append(
            {
                "check_item": "phase1_sku_demand_rows",
                "status": "BLOCKED",
                "reason": "phase1_sku_demand_template.csv has no rows; actual SKU target is required.",
            }
        )
        return pd.DataFrame(), pd.DataFrame(status_rows)

    demand = normalize_keys(demand, ["sku", "region", "channel"])
    required = ["date", "sku", "region", "channel", "actual_demand_kl"]
    missing = [col for col in required if col not in demand.columns]
    if missing:
        status_rows.append(
            {
                "check_item": "phase1_sku_demand_schema",
                "status": "BLOCKED",
                "reason": f"Missing required columns: {','.join(missing)}",
            }
        )
        return pd.DataFrame(), pd.DataFrame(status_rows)

    for col in ["actual_demand_kl", "shipments_kl", "sell_out_kl", "stockout_flag"]:
        demand[col] = pd.to_numeric(demand[col], errors="coerce")

    invalid_target = demand["actual_demand_kl"].isna().sum()
    if invalid_target:
        status_rows.append(
            {
                "check_item": "actual_demand_kl_nulls",
                "status": "FAIL",
                "reason": f"{int(invalid_target)} rows have null actual_demand_kl.",
            }
        )

    model_input = demand.copy()
    inv = build_inventory_features()
    if not inv.empty:
        model_input = model_input.merge(inv, on=["date", "sku", "region"], how="left")
        status_rows.append({"check_item": "inventory_merge", "status": "PASS", "reason": "inventory features merged"})
    else:
        status_rows.append({"check_item": "inventory_merge", "status": "SKIPPED", "reason": "inventory template empty"})

    promo = build_promotion_features()
    if not promo.empty:
        model_input = model_input.merge(promo, on=["date", "sku", "region", "channel"], how="left")
        status_rows.append({"check_item": "promotion_merge", "status": "PASS", "reason": "promotion features merged"})
    else:
        status_rows.append({"check_item": "promotion_merge", "status": "SKIPPED", "reason": "promotion template empty"})

    account = build_account_features()
    if not account.empty:
        model_input = model_input.merge(account, on=["date", "sku", "region", "channel"], how="left")
        status_rows.append({"check_item": "account_merge", "status": "PASS", "reason": "account order features merged"})
    else:
        status_rows.append({"check_item": "account_merge", "status": "SKIPPED", "reason": "account order template empty"})

    tank = build_tank_features()
    if not tank.empty:
        model_input = model_input.merge(tank, on=["date", "sku"], how="left")
        status_rows.append({"check_item": "tank_merge", "status": "PASS", "reason": "tank features merged"})
    else:
        status_rows.append({"check_item": "tank_merge", "status": "SKIPPED", "reason": "tank template empty"})

    model_input["series_id"] = (
        model_input["sku"].astype(str)
        + "|"
        + model_input["region"].astype(str)
        + "|"
        + model_input["channel"].astype(str)
    )
    model_input["month"] = model_input["date"].dt.to_period("M").astype(str)
    model_input = model_input.sort_values(["series_id", "date"]).reset_index(drop=True)
    status_rows.append(
        {
            "check_item": "phase1_model_input_rows",
            "status": "PASS" if len(model_input) else "BLOCKED",
            "reason": f"{len(model_input)} rows generated.",
        }
    )
    return model_input, pd.DataFrame(status_rows)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    model_input, status = build_phase1_model_input()
    model_input.to_csv(DATA_DIR / "phase1_model_input.csv", index=False, encoding="utf-8-sig")
    status.to_csv(OUTPUT_DIR / "phase1_model_input_status.csv", index=False, encoding="utf-8-sig")
    print(f"Wrote {len(model_input)} Phase 1 model input rows")
    print(f"Status: {OUTPUT_DIR / 'phase1_model_input_status.csv'}")


if __name__ == "__main__":
    main()
