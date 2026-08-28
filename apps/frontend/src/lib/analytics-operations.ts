// Mirrors analytics/data.py's NUMERIC_TYPES/CATEGORICAL_TYPES/TEMPORAL_TYPES
// exactly — the backend rejects a column of the wrong kind for a given
// operation with a 400, but filtering the dropdowns to only offer
// eligible columns up front means an operator only ever discovers that
// by reading this list once, not by trial and error against the API.
//
// Shared between /tables/[tableId]/analytics (the interactive runner)
// and the dashboard builder (Unit 4c) — one source of truth for what
// analytics.OPERATIONS accepts, not two copies that can drift.
export const NUMERIC_TYPES = ["integer", "bigint", "decimal"];
export const CATEGORICAL_TYPES = ["text", "varchar", "boolean"];
export const TEMPORAL_TYPES = ["date", "datetime"];

export type FieldSpec =
  | { kind: "column"; key: string; label: string; types: string[] }
  | { kind: "number"; key: string; label: string; default?: number };

export type OperationSpec = {
  key: string;
  operation: string; // the actual OPERATIONS registry key -- may repeat across specs (t_test)
  label: string;
  category: "Descriptive" | "Statistical";
  fields: FieldSpec[];
};

export const OPERATIONS: OperationSpec[] = [
  { key: "count", operation: "count", label: "Row count", category: "Descriptive", fields: [] },
  {
    key: "distinct_count",
    operation: "distinct_count",
    label: "Distinct value count",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: [...NUMERIC_TYPES, ...CATEGORICAL_TYPES] }],
  },
  {
    key: "missing",
    operation: "missing",
    label: "Missing values",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: [...NUMERIC_TYPES, ...CATEGORICAL_TYPES, ...TEMPORAL_TYPES] }],
  },
  {
    key: "frequency_distribution",
    operation: "frequency_distribution",
    label: "Frequency distribution",
    category: "Descriptive",
    fields: [
      { kind: "column", key: "column", label: "Column", types: [...NUMERIC_TYPES, ...CATEGORICAL_TYPES] },
      { kind: "number", key: "top_n", label: "Top N values", default: 10 },
    ],
  },
  {
    key: "sum",
    operation: "sum",
    label: "Sum",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "mean",
    operation: "mean",
    label: "Mean",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "median",
    operation: "median",
    label: "Median",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "min",
    operation: "min",
    label: "Minimum",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "max",
    operation: "max",
    label: "Maximum",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "stdev",
    operation: "stdev",
    label: "Standard deviation",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "variance",
    operation: "variance",
    label: "Variance",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "outlier_detection",
    operation: "outlier_detection",
    label: "Outlier detection (IQR)",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "pearson_correlation",
    operation: "pearson_correlation",
    label: "Pearson correlation",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_x", label: "Column X", types: NUMERIC_TYPES },
      { kind: "column", key: "column_y", label: "Column Y", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "spearman_correlation",
    operation: "spearman_correlation",
    label: "Spearman correlation",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_x", label: "Column X", types: NUMERIC_TYPES },
      { kind: "column", key: "column_y", label: "Column Y", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "linear_regression",
    operation: "linear_regression",
    label: "Linear regression",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_x", label: "Column X (predictor)", types: NUMERIC_TYPES },
      { kind: "column", key: "column_y", label: "Column Y (outcome)", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "t_test_two_columns",
    operation: "t_test",
    label: "T-test (two columns)",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column", label: "Column A", types: NUMERIC_TYPES },
      { kind: "column", key: "column_b", label: "Column B", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "t_test_grouped",
    operation: "t_test",
    label: "T-test (one column, grouped)",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column", label: "Value column", types: NUMERIC_TYPES },
      { kind: "column", key: "group_column", label: "Group column (exactly 2 groups)", types: CATEGORICAL_TYPES },
    ],
  },
  {
    key: "chi_square",
    operation: "chi_square",
    label: "Chi-square (independence)",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_a", label: "Column A", types: CATEGORICAL_TYPES },
      { kind: "column", key: "column_b", label: "Column B", types: CATEGORICAL_TYPES },
    ],
  },
  {
    key: "anova",
    operation: "anova",
    label: "One-way ANOVA",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column", label: "Value column", types: NUMERIC_TYPES },
      { kind: "column", key: "group_column", label: "Group column", types: CATEGORICAL_TYPES },
    ],
  },
  {
    key: "time_series_summary",
    operation: "time_series_summary",
    label: "Time series summary",
    category: "Statistical",
    fields: [
      { kind: "column", key: "date_column", label: "Date column", types: TEMPORAL_TYPES },
      { kind: "column", key: "value_column", label: "Value column", types: NUMERIC_TYPES },
      { kind: "number", key: "window", label: "Moving average window", default: 7 },
    ],
  },
];
