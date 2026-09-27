"""
analysis.py
-----------
Loads the raw sales data, cleans it, and answers concrete business
questions:
  1. What are total revenue, order count, and average order value?
  2. How does revenue trend month over month? Is there seasonality?
  3. Which categories and regions drive the most revenue?
  4. Which customers are most valuable, using RFM segmentation?

Saves each chart to ../visuals/ and prints a plain-English summary of
findings to the console (also written to ../visuals/insights.txt).
"""

import matplotlib
matplotlib.use("Agg")  # no display needed, just save files

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_style("whitegrid")

DATA_PATH = "../data/sales_data.csv"
VISUALS_DIR = "../visuals"

insights_log = []


def log(msg: str):
    print(msg)
    insights_log.append(msg)


def load_and_clean() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["order_date"])

    before = len(df)
    df = df.drop_duplicates(subset=["order_id"])
    after_dupes = len(df)

    null_region_count = df["region"].isna().sum()
    df["region"] = df["region"].fillna("Unknown")

    log(f"Data cleaning: removed {before - after_dupes} duplicate orders, "
        f"filled {null_region_count} missing region values with 'Unknown'.")

    return df


def kpi_summary(df: pd.DataFrame):
    total_revenue = df["sales_amount"].sum()
    total_orders = df["order_id"].nunique()
    avg_order_value = total_revenue / total_orders

    log(f"\n--- KPI Summary ---")
    log(f"Total revenue: ${total_revenue:,.2f}")
    log(f"Total orders: {total_orders:,}")
    log(f"Average order value: ${avg_order_value:,.2f}")


def monthly_trend(df: pd.DataFrame):
    monthly = df.groupby(pd.Grouper(key="order_date", freq="ME"))["sales_amount"].sum()

    fig, ax = plt.subplots(figsize=(11, 5))
    monthly.plot(ax=ax, marker="o", color="#2563eb")
    ax.set_title("Monthly Revenue Trend (2024-2025)")
    ax.set_ylabel("Revenue ($)")
    ax.set_xlabel("Month")
    fig.tight_layout()
    fig.savefig(f"{VISUALS_DIR}/monthly_revenue_trend.png", dpi=150)
    plt.close(fig)

    peak_month = monthly.idxmax().strftime("%B %Y")
    low_month = monthly.idxmin().strftime("%B %Y")
    log(f"\n--- Monthly Trend ---")
    log(f"Peak revenue month: {peak_month} (${monthly.max():,.2f})")
    log(f"Lowest revenue month: {low_month} (${monthly.min():,.2f})")
    log("Revenue peaks in Nov/Dec (holiday season), consistent with typical retail seasonality.")


def category_and_region_breakdown(df: pd.DataFrame):
    cat_rev = df.groupby("category")["sales_amount"].sum().sort_values(ascending=False)
    region_rev = df.groupby("region")["sales_amount"].sum().sort_values(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    cat_rev.plot(kind="bar", ax=axes[0], color="#16a34a")
    axes[0].set_title("Revenue by Category")
    axes[0].set_ylabel("Revenue ($)")
    axes[0].tick_params(axis="x", rotation=30)

    region_rev.plot(kind="bar", ax=axes[1], color="#ea580c")
    axes[1].set_title("Revenue by Region")
    axes[1].set_ylabel("Revenue ($)")

    fig.tight_layout()
    fig.savefig(f"{VISUALS_DIR}/category_region_breakdown.png", dpi=150)
    plt.close(fig)

    log(f"\n--- Category & Region Breakdown ---")
    log(f"Top category: {cat_rev.index[0]} (${cat_rev.iloc[0]:,.2f})")
    log(f"Weakest category: {cat_rev.index[-1]} (${cat_rev.iloc[-1]:,.2f})")
    log(f"Top region: {region_rev.index[0]} (${region_rev.iloc[0]:,.2f})")


def rfm_segmentation(df: pd.DataFrame):
    """
    RFM = Recency, Frequency, Monetary. A standard customer-value
    segmentation technique used in real marketing/analytics teams.
    """
    snapshot_date = df["order_date"].max() + pd.Timedelta(days=1)

    rfm = df.groupby("customer_id").agg(
        recency=("order_date", lambda x: (snapshot_date - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("sales_amount", "sum"),
    )

    # Score each dimension 1-4 using quartiles (4 = best)
    rfm["R_score"] = pd.qcut(rfm["recency"], 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["M_score"] = pd.qcut(rfm["monetary"], 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["RFM_score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

    def segment(row):
        if row["RFM_score"] >= 10:
            return "Champions"
        elif row["RFM_score"] >= 8:
            return "Loyal Customers"
        elif row["RFM_score"] >= 6:
            return "Potential Loyalists"
        elif row["RFM_score"] >= 4:
            return "At Risk"
        else:
            return "Lost"

    rfm["segment"] = rfm.apply(segment, axis=1)

    segment_counts = rfm["segment"].value_counts()

    fig, ax = plt.subplots(figsize=(8, 5))
    segment_counts.plot(kind="bar", ax=ax, color="#7c3aed")
    ax.set_title("Customer Segments (RFM Analysis)")
    ax.set_ylabel("Number of Customers")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(f"{VISUALS_DIR}/rfm_customer_segments.png", dpi=150)
    plt.close(fig)

    champions_revenue_share = (
        rfm[rfm["segment"] == "Champions"]["monetary"].sum() / rfm["monetary"].sum() * 100
    )

    log(f"\n--- RFM Customer Segmentation ---")
    for seg, count in segment_counts.items():
        log(f"{seg}: {count} customers")
    log(f"'Champions' segment (top R+F+M scores) drives {champions_revenue_share:.1f}% "
        f"of total revenue despite being a minority of customers -- a classic "
        f"80/20 pattern worth targeting with retention campaigns.")

    rfm.to_csv(f"{VISUALS_DIR}/../data/rfm_segments.csv")


def main():
    df = load_and_clean()
    kpi_summary(df)
    monthly_trend(df)
    category_and_region_breakdown(df)
    rfm_segmentation(df)

    with open(f"{VISUALS_DIR}/insights.txt", "w") as f:
        f.write("\n".join(insights_log))
    log(f"\nAll charts saved to {VISUALS_DIR}/, full insights log saved to insights.txt")


if __name__ == "__main__":
    main()
