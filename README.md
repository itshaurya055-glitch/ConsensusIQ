# Goldman SQL Engine

A lightweight SQL-like query engine written in Python. It reads one SQL statement from standard input, executes it against the JSON files in this folder, and prints the result as CSV-style text.

## What’s in the project

- `sql_engine.py` - the query engine
- `users_public.json` - sample user data
- `transactions_public.json` - sample transaction data
- `products_public.json` - sample product data
- `reviews_public.json` - sample review data

## How it works

The engine treats each JSON file as a table. For example:

- `FROM users` loads `users.json` if it exists, otherwise `users_public.json`
- `FROM transactions` loads `transactions.json` or `transactions_public.json`
- `FROM products` loads `products.json` or `products_public.json`
- `FROM reviews` loads `reviews.json` or `reviews_public.json`

The script prints the output with a header row followed by rows of comma-separated values.

## Requirements

- Python 3.8+ recommended
- No third-party packages required

## Run it

Run the engine from the project folder and pipe in a SQL query:

```bash
python sql_engine.py
```

Then type a query and press Enter, or pipe one in directly:

```bash
echo "SELECT u.name AS name, u.location AS location FROM users u ORDER BY name LIMIT 5" | python sql_engine.py
```

## Supported SQL features

- `SELECT`
- `FROM`
- `JOIN` and `INNER JOIN`
- `WHERE`
- `GROUP BY`
- `ORDER BY`
- `LIMIT`
- Aggregate functions:
  - `COUNT(*)`
  - `SUM(...)`
  - `AVG(...)`
  - `MIN(...)`
  - `MAX(...)`

## Query rules to know

This parser is a bit strict, so the query should follow these patterns:

- Every selected column or aggregate must use `AS <alias>`.
- `FROM` must include a table name and an alias, such as `FROM users u`.
- Each `JOIN` must also include a table name, an alias, and an `ON` clause.
- `ORDER BY` is required.
- `GROUP BY` is optional, but if you use aggregates without `GROUP BY`, the engine will still aggregate over the current result set.
- Comparisons support `=`, `<>`, `>`, `>=`, `<`, and `<=`.

## Example queries

Basic filter:

```sql
SELECT u.name AS name, u.age AS age, u.location AS location
FROM users u
WHERE u.location = 'Delhi'
ORDER BY name
LIMIT 10
```

Join:

```sql
SELECT t.transaction_id AS transaction_id, u.name AS user_name, t.total_amount AS total_amount
FROM transactions t
JOIN users u ON t.user_id = u.user_id
ORDER BY total_amount DESC
LIMIT 5
```

Aggregation:

```sql
SELECT p.category AS category, COUNT(*) AS total_products
FROM products p
GROUP BY p.category
ORDER BY total_products DESC
```

Join with reviews:

```sql
SELECT p.name AS product_name, AVG(r.rating) AS avg_rating
FROM products p
JOIN reviews r ON p.id = r.product_id
GROUP BY p.name
ORDER BY avg_rating DESC
```

## Notes

- Numeric aggregate results are rounded to 2 decimal places.
- Column lookup can use table aliases, which is the safest approach when joining tables.
- If a table name does not match an exact JSON file, the engine looks for a file whose name starts with the table name plus an underscore.
