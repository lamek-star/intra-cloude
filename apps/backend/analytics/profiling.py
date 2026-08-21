"""
Automatic dataset profiling — a "Data Quality Report" for a whole table
in one call (Section 23 of the master prompt), computed from a single
capped fetch of every column rather than one query per column.
"""

from collections import Counter

import numpy as np

from .data import CATEGORICAL_TYPES, NUMERIC_TYPES, fetch_columns


def profile_table(table) -> dict:
    columns = list(table.columns.order_by("created_at"))
    column_names = [c.name for c in columns]
    fetched = fetch_columns(table, column_names)
    rows = fetched["rows"]
    total = len(rows)

    column_profiles = []
    for i, column in enumerate(columns):
        values = [row[i] for row in rows]
        non_null = [v for v in values if v is not None]
        missing = total - len(non_null)
        profile = {
            "name": column.name,
            "data_type": column.data_type,
            "missing_count": missing,
            "null_percentage": round(100 * missing / total, 2) if total else 0.0,
            "unique_count": len(set(non_null)),
        }

        if column.data_type in NUMERIC_TYPES and non_null:
            arr = np.array([float(v) for v in non_null], dtype=float)
            q1, q3 = np.percentile(arr, [25, 75]) if len(arr) >= 2 else (float(arr[0]), float(arr[0]))
            iqr = q3 - q1
            outlier_count = (
                int(np.sum((arr < q1 - 1.5 * iqr) | (arr > q3 + 1.5 * iqr))) if len(arr) >= 4 else 0
            )
            profile.update(
                {
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "mean": float(np.mean(arr)),
                    "median": float(np.median(arr)),
                    "stdev": float(np.std(arr, ddof=1)) if len(arr) >= 2 else 0.0,
                    "potential_outlier_count": outlier_count,
                }
            )
        elif column.data_type in CATEGORICAL_TYPES and non_null:
            counts = Counter(non_null)
            profile["top_values"] = [{"value": v, "count": c} for v, c in counts.most_common(5)]

        column_profiles.append(profile)

    return {
        "table": table.name,
        "row_count": fetched["total_rows"],
        "column_count": len(columns),
        "truncated": fetched["truncated"],
        "sampled_rows": total,
        "columns": column_profiles,
    }
