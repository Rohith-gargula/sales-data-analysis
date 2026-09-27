"""
generate_data.py
-----------------
Generates a realistic synthetic retail sales transaction dataset:
2 years of daily transactions across multiple product categories,
regions, and customers -- with built-in seasonality, a growth trend,
and some intentional data-quality issues (nulls, duplicates) so the
analysis has real cleaning work to do, not a pre-cleaned toy dataset.
"""

import numpy as np
import pandas as pd

np.random.seed(42)

CATEGORIES = {
    "Electronics": (80, 600),
    "Home & Kitchen": (15, 150),
    "Apparel": (10, 90),
    "Sports & Outdoors": (20, 200),
    "Beauty": (5, 60),
}

REGIONS = ["North", "South", "East", "West", "Central"]

N_CUSTOMERS = 800
N_TRANSACTIONS = 15000

START_DATE = pd.Timestamp("2024-01-01")
END_DATE = pd.Timestamp("2025-12-31")
DATE_RANGE_DAYS = (END_DATE - START_DATE).days


def seasonal_multiplier(date: pd.Timestamp) -> float:
    """Boost sales in Nov-Dec (holiday season) and dip slightly in Feb."""
    month = date.month
    if month in (11, 12):
        return 1.6
    if month == 2:
        return 0.8
    if month in (6, 7):
        return 1.15  # summer bump
    return 1.0


def generate() -> pd.DataFrame:
    customer_ids = [f"CUST{str(i).zfill(4)}" for i in range(1, N_CUSTOMERS + 1)]

    rows = []
    for i in range(N_TRANSACTIONS):
        # Slight upward trend over the 2 years by biasing random days later
        day_offset = int(np.random.beta(1.4, 1.0) * DATE_RANGE_DAYS)
        order_date = START_DATE + pd.Timedelta(days=day_offset)

        category = np.random.choice(list(CATEGORIES.keys()), p=[0.28, 0.22, 0.25, 0.15, 0.10])
        low, high = CATEGORIES[category]
        base_price = np.random.uniform(low, high)

        mult = seasonal_multiplier(order_date)
        quantity = max(1, int(np.random.poisson(1.5 * mult)))
        unit_price = round(base_price, 2)

        rows.append(
            {
                "order_id": f"ORD{100000 + i}",
                "order_date": order_date,
                "customer_id": np.random.choice(customer_ids),
                "region": np.random.choice(REGIONS),
                "category": category,
                "quantity": quantity,
                "unit_price": unit_price,
                "sales_amount": round(quantity * unit_price, 2),
            }
        )

    df = pd.DataFrame(rows)

    # Inject realistic messiness for the cleaning step to handle
    null_idx = np.random.choice(df.index, size=int(0.02 * len(df)), replace=False)
    df.loc[null_idx, "region"] = None

    dupe_rows = df.sample(frac=0.01, random_state=1)
    df = pd.concat([df, dupe_rows], ignore_index=True)

    return df


if __name__ == "__main__":
    df = generate()
    df.to_csv("../data/sales_data.csv", index=False)
    print(f"Generated {len(df)} transaction rows -> data/sales_data.csv")
