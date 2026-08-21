"""
The fixed, versioned registry of analytics operations (Section 27 of
the master prompt: "expose only approved analytics operations through
validated server-side APIs" — never arbitrary code, not even arbitrary
SQL). Each function takes `(table, params)` and returns a JSON-safe
dict. Statistical (as opposed to purely descriptive) operations always
include `method`, `sample_size`, `assumptions`, and
`interpretation_note` fields — Section 22's requirement that the
software "must never present correlation as proof of causation" is
enforced here, at the one place every caller's result passes through,
not left to whatever UI happens to render it later.
"""

from collections import Counter

import numpy as np
from scipy import stats as scipy_stats

from .data import (
    CATEGORICAL_TYPES,
    NUMERIC_TYPES,
    TEMPORAL_TYPES,
    AnalyticsValidationError,
    fetch_columns,
    get_column,
    require_types,
)

CAUSATION_NOTE = (
    "Correlation/association does not establish causation. Confounding variables, "
    "reverse causation, and coincidence can all produce a statistically significant result."
)


def _numeric_series(table, column_name: str) -> tuple[np.ndarray, int, bool]:
    column = get_column(table, column_name)
    require_types(column, NUMERIC_TYPES)
    fetched = fetch_columns(table, [column.name])
    values = np.array(
        [float(row[0]) for row in fetched["rows"] if row[0] is not None], dtype=float
    )
    return values, fetched["total_rows"], fetched["truncated"]


def _require_min_n(values, minimum: int, label: str = "sample") -> None:
    if len(values) < minimum:
        raise AnalyticsValidationError(
            f"{label} has {len(values)} non-null values; at least {minimum} are needed for this operation"
        )


# ---------------------------------------------------------------------------
# Descriptive statistics (Section 21)
# ---------------------------------------------------------------------------


def op_count(table, params):
    column_name = params.get("column")
    if not column_name:
        fetched = fetch_columns(table, [table.columns.order_by("created_at").first().name])
        return {"operation": "count", "count": fetched["total_rows"]}
    column = get_column(table, column_name)
    fetched = fetch_columns(table, [column.name])
    non_null = sum(1 for row in fetched["rows"] if row[0] is not None)
    return {"operation": "count", "column": column.name, "count": non_null, "truncated": fetched["truncated"]}


def op_distinct_count(table, params):
    column = get_column(table, params["column"])
    fetched = fetch_columns(table, [column.name])
    distinct = len({row[0] for row in fetched["rows"]})
    return {
        "operation": "distinct_count",
        "column": column.name,
        "distinct_count": distinct,
        "truncated": fetched["truncated"],
    }


def op_missing(table, params):
    column = get_column(table, params["column"])
    fetched = fetch_columns(table, [column.name])
    total = len(fetched["rows"])
    missing = sum(1 for row in fetched["rows"] if row[0] is None)
    return {
        "operation": "missing",
        "column": column.name,
        "missing_count": missing,
        "null_percentage": round(100 * missing / total, 2) if total else 0.0,
        "truncated": fetched["truncated"],
    }


def op_duplicate_count(table, params):
    column_names = params.get("columns") or [params["column"]]
    columns = [get_column(table, c) for c in column_names]
    fetched = fetch_columns(table, [c.name for c in columns])
    total = len(fetched["rows"])
    distinct = len(set(fetched["rows"]))
    return {
        "operation": "duplicate_count",
        "columns": [c.name for c in columns],
        "duplicate_rows": total - distinct,
        "truncated": fetched["truncated"],
    }


def op_frequency_distribution(table, params):
    column = get_column(table, params["column"])
    require_types(column, CATEGORICAL_TYPES | NUMERIC_TYPES)
    top_n = min(int(params.get("top_n", 10)), 100)
    fetched = fetch_columns(table, [column.name])
    counts = Counter(row[0] for row in fetched["rows"] if row[0] is not None)
    most_common = counts.most_common(top_n)
    return {
        "operation": "frequency_distribution",
        "column": column.name,
        "distribution": [{"value": v, "count": c} for v, c in most_common],
        "distinct_values_total": len(counts),
        "truncated": fetched["truncated"],
    }


def _descriptive_numeric(table, params, op_name, reducer):
    values, total_rows, truncated = _numeric_series(table, params["column"])
    _require_min_n(values, 1)
    return {
        "operation": op_name,
        "column": params["column"],
        "value": reducer(values),
        "sample_size": len(values),
        "truncated": truncated,
    }


def op_sum(table, params):
    return _descriptive_numeric(table, params, "sum", lambda v: float(np.sum(v)))


def op_mean(table, params):
    return _descriptive_numeric(table, params, "mean", lambda v: float(np.mean(v)))


def op_median(table, params):
    return _descriptive_numeric(table, params, "median", lambda v: float(np.median(v)))


def op_min(table, params):
    return _descriptive_numeric(table, params, "min", lambda v: float(np.min(v)))


def op_max(table, params):
    return _descriptive_numeric(table, params, "max", lambda v: float(np.max(v)))


def op_stdev(table, params):
    values, total_rows, truncated = _numeric_series(table, params["column"])
    _require_min_n(values, 2, "column")
    return {
        "operation": "stdev",
        "column": params["column"],
        "value": float(np.std(values, ddof=1)),
        "sample_size": len(values),
        "truncated": truncated,
    }


def op_variance(table, params):
    values, total_rows, truncated = _numeric_series(table, params["column"])
    _require_min_n(values, 2, "column")
    return {
        "operation": "variance",
        "column": params["column"],
        "value": float(np.var(values, ddof=1)),
        "sample_size": len(values),
        "truncated": truncated,
    }


def op_percentiles(table, params):
    values, total_rows, truncated = _numeric_series(table, params["column"])
    _require_min_n(values, 1)
    percentiles = params.get("percentiles", [25, 50, 75])
    if not all(isinstance(p, (int, float)) and 0 <= p <= 100 for p in percentiles):
        raise AnalyticsValidationError("percentiles must be numbers between 0 and 100")
    results = np.percentile(values, percentiles)
    return {
        "operation": "percentiles",
        "column": params["column"],
        "percentiles": {str(p): float(r) for p, r in zip(percentiles, results, strict=True)},
        "sample_size": len(values),
        "truncated": truncated,
    }


def op_outlier_detection(table, params):
    """IQR method: outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]."""
    values, total_rows, truncated = _numeric_series(table, params["column"])
    _require_min_n(values, 4, "column")
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = values[(values < lower) | (values > upper)]
    return {
        "operation": "outlier_detection",
        "column": params["column"],
        "method": "IQR (1.5x, Tukey's fences)",
        "lower_bound": float(lower),
        "upper_bound": float(upper),
        "outlier_count": int(outliers.size),
        "outlier_sample": [float(v) for v in outliers[:50]],
        "sample_size": len(values),
        "truncated": truncated,
        "interpretation_note": (
            "Outliers by this rule are not necessarily errors — verify against domain knowledge "
            "before removing or correcting any of them."
        ),
    }


# ---------------------------------------------------------------------------
# Statistical analysis (Section 22)
# ---------------------------------------------------------------------------


def op_pearson_correlation(table, params):
    x, _, tx = _numeric_series(table, params["column_x"])
    y, _, ty = _numeric_series(table, params["column_y"])
    n = min(len(x), len(y))
    _require_min_n(np.arange(n), 3, "paired sample")
    x, y = x[:n], y[:n]
    r, p = scipy_stats.pearsonr(x, y)
    return {
        "operation": "pearson_correlation",
        "method": "Pearson product-moment correlation",
        "columns": [params["column_x"], params["column_y"]],
        "r": float(r),
        "p_value": float(p),
        "sample_size": n,
        "assumptions": [
            "linear relationship",
            "roughly normally distributed variables",
            "no extreme outliers",
        ],
        "interpretation_note": CAUSATION_NOTE,
        "truncated": tx or ty,
    }


def op_spearman_correlation(table, params):
    x, _, tx = _numeric_series(table, params["column_x"])
    y, _, ty = _numeric_series(table, params["column_y"])
    n = min(len(x), len(y))
    _require_min_n(np.arange(n), 3, "paired sample")
    x, y = x[:n], y[:n]
    r, p = scipy_stats.spearmanr(x, y)
    return {
        "operation": "spearman_correlation",
        "method": "Spearman rank correlation",
        "columns": [params["column_x"], params["column_y"]],
        "rho": float(r),
        "p_value": float(p),
        "sample_size": n,
        "assumptions": ["monotonic relationship (not necessarily linear)"],
        "interpretation_note": CAUSATION_NOTE,
        "truncated": tx or ty,
    }


def op_linear_regression(table, params):
    x, _, tx = _numeric_series(table, params["column_x"])
    y, _, ty = _numeric_series(table, params["column_y"])
    n = min(len(x), len(y))
    _require_min_n(np.arange(n), 3, "paired sample")
    x, y = x[:n], y[:n]
    result = scipy_stats.linregress(x, y)
    return {
        "operation": "linear_regression",
        "method": "Ordinary least squares (simple linear regression)",
        "x_column": params["column_x"],
        "y_column": params["column_y"],
        "slope": float(result.slope),
        "intercept": float(result.intercept),
        "r_squared": float(result.rvalue**2),
        "p_value": float(result.pvalue),
        "std_err": float(result.stderr),
        "sample_size": n,
        "assumptions": [
            "linear relationship between x and y",
            "residuals are independent and roughly normally distributed",
            "constant variance of residuals (homoscedasticity)",
        ],
        "interpretation_note": CAUSATION_NOTE,
        "truncated": tx or ty,
    }


def op_t_test(table, params):
    a, _, ta = _numeric_series(table, params["column"])
    if params.get("column_b"):
        b, _, tb = _numeric_series(table, params["column_b"])
        truncated = ta or tb
    else:
        group_col = get_column(table, params["group_column"])
        require_types(group_col, CATEGORICAL_TYPES)
        value_col = get_column(table, params["column"])
        fetched = fetch_columns(table, [value_col.name, group_col.name])
        groups: dict = {}
        for value, group in fetched["rows"]:
            if value is None or group is None:
                continue
            groups.setdefault(group, []).append(float(value))
        if len(groups) != 2:
            raise AnalyticsValidationError(
                f"group_column {group_col.name!r} has {len(groups)} distinct values; "
                "a two-sample t-test needs exactly 2"
            )
        (label_a, a), (label_b, b) = list(groups.items())
        a, b = np.array(a), np.array(b)
        truncated = fetched["truncated"]

    _require_min_n(a, 2, "group A"), _require_min_n(b, 2, "group B")
    statistic, p_value = scipy_stats.ttest_ind(a, b, equal_var=False)  # Welch's t-test
    return {
        "operation": "t_test",
        "method": "Welch's two-sample t-test (does not assume equal variances)",
        "statistic": float(statistic),
        "p_value": float(p_value),
        "sample_sizes": [len(a), len(b)],
        "assumptions": ["both groups are approximately normally distributed", "observations are independent"],
        "interpretation_note": "A significant result indicates a difference in means, not its cause or size.",
        "truncated": truncated,
    }


def op_chi_square(table, params):
    col_a = get_column(table, params["column_a"])
    col_b = get_column(table, params["column_b"])
    require_types(col_a, CATEGORICAL_TYPES)
    require_types(col_b, CATEGORICAL_TYPES)
    fetched = fetch_columns(table, [col_a.name, col_b.name])
    pairs = [(a, b) for a, b in fetched["rows"] if a is not None and b is not None]
    _require_min_n(pairs, 5, "paired sample")

    values_a = sorted({a for a, _ in pairs})
    values_b = sorted({b for _, b in pairs})
    table_counts = np.zeros((len(values_a), len(values_b)))
    index_a = {v: i for i, v in enumerate(values_a)}
    index_b = {v: i for i, v in enumerate(values_b)}
    for a, b in pairs:
        table_counts[index_a[a], index_b[b]] += 1

    statistic, p_value, dof, _expected = scipy_stats.chi2_contingency(table_counts)
    return {
        "operation": "chi_square",
        "method": "Chi-square test of independence",
        "columns": [col_a.name, col_b.name],
        "statistic": float(statistic),
        "p_value": float(p_value),
        "degrees_of_freedom": int(dof),
        "sample_size": len(pairs),
        "assumptions": ["expected frequency of at least 5 in most contingency-table cells"],
        "interpretation_note": CAUSATION_NOTE,
        "truncated": fetched["truncated"],
    }


def op_anova(table, params):
    value_col = get_column(table, params["column"])
    group_col = get_column(table, params["group_column"])
    require_types(value_col, NUMERIC_TYPES)
    require_types(group_col, CATEGORICAL_TYPES)
    fetched = fetch_columns(table, [value_col.name, group_col.name])
    groups: dict = {}
    for value, group in fetched["rows"]:
        if value is None or group is None:
            continue
        groups.setdefault(group, []).append(float(value))
    if len(groups) < 2:
        raise AnalyticsValidationError(f"group_column {group_col.name!r} needs at least 2 distinct values")
    for label, values in groups.items():
        _require_min_n(values, 2, f"group {label!r}")

    statistic, p_value = scipy_stats.f_oneway(*groups.values())
    return {
        "operation": "anova",
        "method": "One-way ANOVA",
        "value_column": value_col.name,
        "group_column": group_col.name,
        "groups": list(groups.keys()),
        "statistic": float(statistic),
        "p_value": float(p_value),
        "sample_size": sum(len(v) for v in groups.values()),
        "assumptions": [
            "each group is approximately normally distributed",
            "groups have similar variances",
            "observations are independent",
        ],
        "interpretation_note": (
            "A significant result means at least one group's mean differs, not which one or why."
        ),
        "truncated": fetched["truncated"],
    }


def op_time_series_summary(table, params):
    date_col = get_column(table, params["date_column"])
    value_col = get_column(table, params["value_column"])
    require_types(date_col, TEMPORAL_TYPES)
    require_types(value_col, NUMERIC_TYPES)
    window = min(int(params.get("window", 7)), 365)

    fetched = fetch_columns(table, [date_col.name, value_col.name])
    points = sorted(
        ((d, float(v)) for d, v in fetched["rows"] if d is not None and v is not None), key=lambda p: p[0]
    )
    _require_min_n(points, 2, "time series")

    values = np.array([v for _, v in points])
    moving_avg = (
        np.convolve(values, np.ones(window) / window, mode="valid") if len(values) >= window else None
    )
    first, last = values[0], values[-1]
    growth_rate = ((last - first) / first * 100) if first else None

    return {
        "operation": "time_series_summary",
        "date_column": date_col.name,
        "value_column": value_col.name,
        "points": [{"date": str(d), "value": v} for d, v in points],
        "moving_average_window": window,
        "moving_average": [float(v) for v in moving_avg] if moving_avg is not None else None,
        "overall_growth_rate_pct": float(growth_rate) if growth_rate is not None else None,
        "sample_size": len(points),
        "truncated": fetched["truncated"],
    }


OPERATIONS = {
    "count": op_count,
    "distinct_count": op_distinct_count,
    "missing": op_missing,
    "duplicate_count": op_duplicate_count,
    "frequency_distribution": op_frequency_distribution,
    "sum": op_sum,
    "mean": op_mean,
    "median": op_median,
    "min": op_min,
    "max": op_max,
    "stdev": op_stdev,
    "variance": op_variance,
    "percentiles": op_percentiles,
    "outlier_detection": op_outlier_detection,
    "pearson_correlation": op_pearson_correlation,
    "spearman_correlation": op_spearman_correlation,
    "linear_regression": op_linear_regression,
    "t_test": op_t_test,
    "chi_square": op_chi_square,
    "anova": op_anova,
    "time_series_summary": op_time_series_summary,
}
