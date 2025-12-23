# PBI Manager Parallel Delegation and Worker Parallel Tools

This example shows how the PBI Manager, configured with a StrategicPlanner, can run schema and validator concurrently, and how the schema worker executes multiple tools in parallel within a single turn.

## Manager Plan (StrategicPlanner with fan-out)

The PBI Manager's planner returns a plan with `parallel_workers` when tasks are independent:

```json
{
  "plan": {
    "steps": [
      {"action": "list_columns for multiple tables", "worker": "schema", "context": "Sales, Customers, Products, Calendar, Geography"},
      {"action": "list_relationships", "worker": "schema", "context": "List all relationships"},
      {"action": "validate_model", "worker": "validator", "context": "Validate model structure"}
    ],
    "rationale": "Listing and validation can run independently in parallel",
    "primary_worker": "schema",
    "parallel_workers": ["schema", "validator"],
    "task_type": "metadata_with_validation"
  }
}
```

The ManagerAgent delegates to both `schema` and `validator` concurrently and aggregates their results.

## Example User Prompt

“For tables Sales, Customers, Products, Calendar, and Geography, list their columns and also list all relationships.”

## Schema Worker – Function Calling Parallel Tools

With function-calling enabled, the schema worker can emit multiple tool calls in one LLM turn:

```json
[
  {"action": "list_columns", "args": {"table": "Sales"}},
  {"action": "list_columns", "args": {"table": "Customers"}},
  {"action": "list_columns", "args": {"table": "Products"}},
  {"action": "list_columns", "args": {"table": "Calendar"}},
  {"action": "list_columns", "args": {"table": "Geography"}},
  {"action": "list_relationships", "args": {}}
]
```

The Agent executes these 6 tools in parallel and aggregates the results.

## Aggregated Payload (Heterogeneous: Columns + Relationships)

When mixed tools run (list_columns + list_relationships), results are returned as a sectioned payload:

```json
{
  "operation": "display_message",
  "payload": {
    "message": "Completed 6 parallel tool executions: 42 columns, 1 list_relationships call(s)",
    "sections": [
      {
        "type": "columns",
        "count": 42,
        "data": [
          ["Sales", "SalesID", "Int64"],
          ["Sales", "Amount", "Decimal"],
          ["Customers", "CustomerID", "Int64"],
          ["Products", "ProductID", "Int64"],
          ["Calendar", "Date", "Date"],
          ["Geography", "Country", "String"]
          // ...remaining rows elided for brevity
        ]
      },
      {
        "type": "list_relationships",
        "count": 1,
        "results": [
          {
            "relationships": [
              {"fromColumn": "Sales[CustomerID]", "toColumn": "Customers[CustomerID]", "isActive": true, "fromCardinality": "Many"},
              {"fromColumn": "Sales[ProductID]", "toColumn": "Products[ProductID]", "isActive": true, "fromCardinality": "Many"}
              // ...more relationships
            ]
          }
        ]
      }
    ]
  },
  "summary": "Completed 6 parallel tool executions: 42 columns, 1 list_relationships call(s)"
}
```

If the worker only ran `list_columns` calls (homogeneous), the framework would merge all columns into a single `display_table` with headers `["Table", "Column Name", "Data Type"]`.

