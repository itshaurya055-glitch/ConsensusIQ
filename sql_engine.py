"""
SQL Query Engine for JSON files.
Supports: SELECT, WHERE, JOIN (INNER), GROUP BY, ORDER BY, LIMIT,
          Aggregate functions: COUNT(*), SUM, AVG, MIN, MAX
"""

import os
import re
import json
import sys
from collections import defaultdict


# ─────────────────────────────────────────────
# 1. LEXER / TOKENIZER
# ─────────────────────────────────────────────

KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'ON', 'AND', 'GROUP', 'BY',
    'ORDER', 'LIMIT', 'AS', 'ASC', 'DESC', 'INNER'
}

TOKEN_RE = re.compile(
    r"'[^']*'"           # single-quoted string
    r'|"[^"]*"'          # double-quoted string
    r'|<>'               # not-equals
    r'|>='               # >=
    r'|<='               # <=
    r'|[><=,().*]'       # single-char operators + misc
    r'|\d+\.\d+'         # float
    r'|\d+'              # int
    r'|[A-Za-z_][A-Za-z0-9_.]*'  # identifiers (may contain dot)
    , re.IGNORECASE
)

def tokenize(sql):
    raw = TOKEN_RE.findall(sql)
    tokens = []
    for t in raw:
        upper = t.upper()
        if upper in KEYWORDS:
            tokens.append(('KW', upper))
        elif t.startswith("'") or t.startswith('"'):
            tokens.append(('STR', t[1:-1]))
        elif re.fullmatch(r'\d+\.\d+', t):
            tokens.append(('NUM', float(t)))
        elif re.fullmatch(r'\d+', t):
            tokens.append(('NUM', int(t)))
        elif t in ('<>', '>=', '<=', '>', '<', '='):
            tokens.append(('OP', t))
        elif t in (',', '(', ')', '.', '*'):
            tokens.append(('PUNCT', t))
        elif '.' in t:
            # dotted identifier like p.price -> split into ID PUNCT('.') ID
            parts = t.split('.')
            for i, part in enumerate(parts):
                pu = part.upper()
                if pu in KEYWORDS:
                    tokens.append(('KW', pu))
                else:
                    tokens.append(('ID', part))
                if i < len(parts) - 1:
                    tokens.append(('PUNCT', '.'))
        else:
            tokens.append(('ID', t))
    return tokens


# ─────────────────────────────────────────────
# 2. PARSER  ->  AST (plain dicts)
# ─────────────────────────────────────────────

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, kind=None, value=None):
        tok = self.tokens[self.pos]
        if kind and tok[0] != kind:
            raise SyntaxError(f"Expected token kind {kind}, got {tok}")
        if value and tok[1].upper() != value.upper():
            raise SyntaxError(f"Expected token value {value!r}, got {tok[1]!r}")
        self.pos += 1
        return tok

    def match(self, kind, value=None):
        tok = self.peek()
        if tok is None:
            return False
        if tok[0] != kind:
            return False
        if value and tok[1].upper() != value.upper():
            return False
        return True

    def parse_col_ref(self):
        """Returns (table_alias, col_name) tuple."""
        first = self.consume('ID')
        if self.match('PUNCT', '.'):
            self.consume('PUNCT', '.')
            second = self.consume('ID')
            return (first[1], second[1])
        return (None, first[1])

    def parse_expression_item(self):
        """Returns dict with keys: expr_type, alias (set later)"""
        tok = self.peek()
        # Aggregate function?
        if tok and tok[0] == 'ID':
            func_name = tok[1].upper()
            if func_name in ('COUNT', 'SUM', 'AVG', 'MIN', 'MAX'):
                if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1] == ('PUNCT', '('):
                    self.consume('ID')           # function name
                    self.consume('PUNCT', '(')
                    if func_name == 'COUNT':
                        self.consume('PUNCT', '*')
                        self.consume('PUNCT', ')')
                        return {'expr_type': 'agg', 'func': 'COUNT', 'col': None}
                    else:
                        col_ref = self.parse_col_ref()
                        self.consume('PUNCT', ')')
                        return {'expr_type': 'agg', 'func': func_name, 'col': col_ref}
        # Plain column reference
        col_ref = self.parse_col_ref()
        return {'expr_type': 'col', 'col': col_ref}

    def parse_select_list(self):
        items = []
        while True:
            item = self.parse_expression_item()
            self.consume('KW', 'AS')
            alias_tok = self.consume('ID')
            item['alias'] = alias_tok[1]
            items.append(item)
            if not self.match('PUNCT', ','):
                break
            self.consume('PUNCT', ',')
        return items

    def parse_condition(self, valid_aliases=None):
        """One condition: alias.col OP value|alias.col"""
        col_ref = self.parse_col_ref()
        op_tok = self.consume('OP')
        op = op_tok[1]
        # RHS: alias.col or literal value
        rhs_tok = self.peek()
        if rhs_tok and rhs_tok[0] == 'ID':
            # Peek ahead to see if next is a dot (alias.col pattern)
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1] == ('PUNCT', '.'):
                rhs_col = self.parse_col_ref()
                return {'lhs': col_ref, 'op': op, 'rhs_type': 'col', 'rhs': rhs_col}
            else:
                # bare identifier -> treat as string value
                val = self.consume('ID')[1]
                return {'lhs': col_ref, 'op': op, 'rhs_type': 'val', 'rhs': val}
        # STR or NUM literal
        val_tok = self.consume()
        return {'lhs': col_ref, 'op': op, 'rhs_type': 'val', 'rhs': val_tok[1]}

    def parse_conditions(self, valid_aliases=None):
        conds = [self.parse_condition(valid_aliases)]
        while self.match('KW', 'AND'):
            self.consume('KW', 'AND')
            conds.append(self.parse_condition(valid_aliases))
        return conds

    def parse(self):
        ast = {}

        # SELECT
        self.consume('KW', 'SELECT')
        ast['select'] = self.parse_select_list()

        # FROM table alias
        self.consume('KW', 'FROM')
        table_name_tok = self.consume('ID')
        table_alias_tok = self.consume('ID')
        ast['from'] = {'table': table_name_tok[1], 'alias': table_alias_tok[1]}

        # JOINs
        joins = []
        while self.match('KW', 'JOIN') or self.match('KW', 'INNER'):
            if self.match('KW', 'INNER'):
                self.consume('KW', 'INNER')
            self.consume('KW', 'JOIN')
            jtable_tok = self.consume('ID')
            jalias_tok = self.consume('ID')
            self.consume('KW', 'ON')
            conditions = self.parse_conditions()
            joins.append({
                'table': jtable_tok[1],
                'alias': jalias_tok[1],
                'on': conditions
            })
        ast['joins'] = joins

        # WHERE
        if self.match('KW', 'WHERE'):
            self.consume('KW', 'WHERE')
            ast['where'] = self.parse_conditions()
        else:
            ast['where'] = []

        # GROUP BY
        if self.match('KW', 'GROUP'):
            self.consume('KW', 'GROUP')
            self.consume('KW', 'BY')
            group_cols = []
            while True:
                group_cols.append(self.parse_col_ref())
                if not self.match('PUNCT', ','):
                    break
                self.consume('PUNCT', ',')
            ast['group_by'] = group_cols
        else:
            ast['group_by'] = []

        # ORDER BY
        self.consume('KW', 'ORDER')
        self.consume('KW', 'BY')
        order_items = []
        while True:
            alias_tok = self.consume('ID')
            direction = 'ASC'
            if self.match('KW', 'ASC') or self.match('KW', 'DESC'):
                direction = self.consume('KW')[1].upper()
            order_items.append({'alias': alias_tok[1], 'dir': direction})
            if not self.match('PUNCT', ','):
                break
            self.consume('PUNCT', ',')
        ast['order_by'] = order_items

        # LIMIT
        if self.match('KW', 'LIMIT'):
            self.consume('KW', 'LIMIT')
            n_tok = self.consume('NUM')
            ast['limit'] = int(n_tok[1])
        else:
            ast['limit'] = None

        return ast


# ─────────────────────────────────────────────
# 3. DATA LOADER
# ─────────────────────────────────────────────

def load_table(table_name, data_dir):
    """Load JSON file for a table.
    Matches any .json file whose stem equals table_name or starts with table_name + '_'.
    Priority: exact match first, then prefix match.
    """
    name_lower = table_name.lower()
    exact = os.path.join(data_dir, f"{table_name}.json")
    if os.path.exists(exact):
        with open(exact) as f:
            return json.load(f)

    try:
        all_files = os.listdir(data_dir)
    except OSError:
        all_files = []

    for fname in sorted(all_files):
        if not fname.lower().endswith('.json'):
            continue
        stem = fname.lower()[:-5]
        if stem == name_lower or stem.startswith(name_lower + '_'):
            with open(os.path.join(data_dir, fname)) as f:
                return json.load(f)

    raise FileNotFoundError(
        f"No JSON file found for table '{table_name}' in '{data_dir}'. "
        f"JSON files present: {[f for f in all_files if f.endswith('.json')]}"
    )


# ─────────────────────────────────────────────
# 4. EVALUATOR
# ─────────────────────────────────────────────

def get_value(row, col_ref):
    """col_ref = (alias, col_name). Row keys are 'alias.col'."""
    alias, col = col_ref
    if alias:
        return row.get(f"{alias}.{col}")
    for k, v in row.items():
        if k.split('.')[-1] == col:
            return v
    return None


def compare(lhs_val, op, rhs_val):
    # Numeric coercion
    if isinstance(lhs_val, (int, float)) and isinstance(rhs_val, (int, float)):
        lhs_val = float(lhs_val)
        rhs_val = float(rhs_val)
    elif isinstance(lhs_val, str) and isinstance(rhs_val, (int, float)):
        try:
            lhs_val = float(lhs_val)
        except (ValueError, TypeError):
            pass
    elif isinstance(rhs_val, str) and isinstance(lhs_val, (int, float)):
        try:
            rhs_val = float(rhs_val)
        except (ValueError, TypeError):
            pass

    if lhs_val is None or rhs_val is None:
        return False

    if op == '=':   return lhs_val == rhs_val
    if op == '<>':  return lhs_val != rhs_val
    if op == '>':   return lhs_val > rhs_val
    if op == '>=':  return lhs_val >= rhs_val
    if op == '<':   return lhs_val < rhs_val
    if op == '<=':  return lhs_val <= rhs_val
    return False


def eval_condition(row, cond):
    lhs_val = get_value(row, cond['lhs'])
    if cond['rhs_type'] == 'col':
        rhs_val = get_value(row, cond['rhs'])
    else:
        rhs_val = cond['rhs']
    return compare(lhs_val, cond['op'], rhs_val)


def prefix_row(record, alias):
    return {f"{alias}.{k}": v for k, v in record.items()}


def execute(ast, data_dir):
    # Load base table
    base = load_table(ast['from']['table'], data_dir)
    base_alias = ast['from']['alias']
    rows = [prefix_row(r, base_alias) for r in base]

    # INNER JOINs
    for join in ast['joins']:
        join_data = load_table(join['table'], data_dir)
        join_alias = join['alias']
        join_rows = [prefix_row(r, join_alias) for r in join_data]
        result = []
        for row in rows:
            for jr in join_rows:
                combined = {**row, **jr}
                if all(eval_condition(combined, c) for c in join['on']):
                    result.append(combined)
        rows = result

    # WHERE
    if ast['where']:
        rows = [r for r in rows if all(eval_condition(r, c) for c in ast['where'])]

    # GROUP BY + Aggregates
    select_items = ast['select']
    has_agg = any(item['expr_type'] == 'agg' for item in select_items)

    if ast['group_by'] or has_agg:
        group_keys = ast['group_by']

        def group_key_fn(row):
            return tuple(get_value(row, g) for g in group_keys)

        groups = defaultdict(list)
        for row in rows:
            groups[group_key_fn(row)].append(row)

        result_rows = []
        for key, group_rows in groups.items():
            out_row = {}
            for item in select_items:
                alias = item['alias']
                if item['expr_type'] == 'col':
                    out_row[alias] = get_value(group_rows[0], item['col'])
                else:
                    func = item['func']
                    col = item['col']
                    if func == 'COUNT':
                        out_row[alias] = len(group_rows)
                    else:
                        vals = [get_value(r, col) for r in group_rows
                                if get_value(r, col) is not None]
                        fvals = [float(x) for x in vals]
                        if func == 'SUM':
                            v = sum(fvals)
                        elif func == 'AVG':
                            v = sum(fvals) / len(fvals) if fvals else 0.0
                        elif func == 'MIN':
                            v = min(fvals) if fvals else None
                        elif func == 'MAX':
                            v = max(fvals) if fvals else None
                        out_row[alias] = round(v, 2) if v is not None else None
            result_rows.append(out_row)
        rows = result_rows
    else:
        result_rows = []
        for row in rows:
            out_row = {}
            for item in select_items:
                out_row[item['alias']] = get_value(row, item['col'])
            result_rows.append(out_row)
        rows = result_rows

    # ORDER BY
    for order in reversed(ast['order_by']):
        col = order['alias']
        reverse = (order['dir'] == 'DESC')
        rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=reverse)

    # LIMIT
    if ast['limit'] is not None:
        rows = rows[:ast['limit']]

    return rows, [item['alias'] for item in select_items]


# ─────────────────────────────────────────────
# 5. OUTPUT FORMATTER
# ─────────────────────────────────────────────

def format_value(v):
    if v is None:
        return ''
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def render_output(rows, columns):
    lines = [','.join(columns)]
    for row in rows:
        vals = [format_value(row.get(c)) for c in columns]
        lines.append(','.join(vals))
    return '\n'.join(lines)


# ─────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────

def main():
    sql = input().strip()
    data_dir = os.getcwd()

    tokens = tokenize(sql)
    parser = Parser(tokens)
    ast = parser.parse()

    rows, columns = execute(ast, data_dir)
    print(render_output(rows, columns))


if __name__ == '__main__':
    main()