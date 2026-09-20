"""
In-Memory Search Processing Language (SPL) Query & Pipeline Engine (NetSpout)
Parses and executes real-time SPL queries over simulated telemetry and log events:
  - Base filters: sourcetype=..., action=..., keyword matches, boolean expressions (AND, OR, NOT).
  - Pipe operations:
    * | stats count, sum(x), avg(x), max(x), min(x), dc(x) by group_fields
    * | where <numeric/string expression>
    * | eval <field> = <expression>
    * | table <field1>, <field2>, ...
    * | sort <+/-><field>
    * | head <n> / tail <n>
    * | top <n> <field> / rare <field>
    * | timechart span=<sec> count by <field>

Author: Mahamudul Chowdhury (mchowdhury@splunk.com)
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class SPLExecutionEngine:
    """
    Executes on-the-fly Search Processing Language (SPL) pipelines.
    """

    @staticmethod
    def _extract_event_fields(event: Any) -> Dict[str, Any]:
        """Flattens LogEntry object or dict into a standard key-value map."""
        if hasattr(event, "dict"):
            d = event.dict()
        elif isinstance(event, dict):
            d = dict(event)
        else:
            d = getattr(event, "__dict__", {})

        fields = {k: v for k, v in d.items() if not k.startswith("_")}
        
        # Parse extra key=value pairs from raw_log if present
        raw = str(fields.get("raw_log", fields.get("data", "")))
        if raw:
            # Match standard key=value or key="value"
            for m in re.finditer(r'([a-zA-Z0-9_\-\.]+)=(?:"([^"]*)"|([^\s]+))', raw):
                k = m.group(1)
                v = m.group(2) if m.group(2) is not None else m.group(3)
                if k not in fields:
                    fields[k] = v

            # If CSV Pan-OS log, extract known positional fields
            if raw.startswith("1,") and "," in raw:
                parts = raw.split(",")
                if len(parts) > 30:
                    fields["src"] = fields.get("src", parts[7] if len(parts) > 7 else "")
                    fields["dest"] = fields.get("dest", parts[8] if len(parts) > 8 else "")
                    fields["app"] = fields.get("app", parts[31] if len(parts) > 31 else "")
                    fields["action"] = fields.get("action", parts[30] if len(parts) > 30 else "")

        # Aliases for CIM consistency
        if "src_ip" in fields and "src" not in fields:
            fields["src"] = fields["src_ip"]
        if "dest_ip" in fields and "dest" not in fields:
            fields["dest"] = fields["dest_ip"]
        if "timestamp" in fields and "_time" not in fields:
            fields["_time"] = fields["timestamp"]

        return fields

    def execute(self, query: str, events: List[Any]) -> Dict[str, Any]:
        """
        Executes an SPL query against a dataset of events and returns structured tabular results.
        """
        start_t = time.perf_counter()
        query = (query or "").strip()
        
        if not query or query == "*":
            pipe_chunks = ["*"]
        else:
            pipe_chunks = [p.strip() for p in query.split("|")]

        known_commands = {'stats', 'eval', 'where', 'table', 'sort', 'head', 'timechart', 'dedup', 'spath', 'fields'}
        first_word = pipe_chunks[0].split()[0].lower() if pipe_chunks[0].split() else ''
        if first_word in known_commands:
            base_search = '*'
            pipes = pipe_chunks
        else:
            base_search = pipe_chunks[0]
            pipes = pipe_chunks[1:]

        # Step 1: Execute Base Search Filter
        filtered_records = []
        total_scanned = len(events)

        for ev in events:
            f_map = self._extract_event_fields(ev)
            if self._matches_search(base_search, f_map):
                filtered_records.append(f_map)

        total_matched = len(filtered_records)
        current_rows = filtered_records
        chart_type = None

        # Step 2: Pipeline execution
        for pipe in pipes:
            p_clean = pipe.strip()
            if not p_clean:
                continue

            cmd_parts = p_clean.split(None, 1)
            cmd = cmd_parts[0].lower()
            args = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

            if cmd == "stats":
                current_rows, chart_type = self._exec_stats(args, current_rows)
            elif cmd == "where":
                current_rows = self._exec_where(args, current_rows)
            elif cmd == "eval":
                current_rows = self._exec_eval(args, current_rows)
            elif cmd == "table":
                current_rows = self._exec_table(args, current_rows)
            elif cmd == "sort":
                current_rows = self._exec_sort(args, current_rows)
            elif cmd == "head":
                try:
                    limit = int(args.split()[0])
                    current_rows = current_rows[:limit]
                except Exception:
                    pass
            elif cmd == "tail":
                try:
                    limit = int(args.split()[0])
                    current_rows = current_rows[-limit:]
                except Exception:
                    pass
            elif cmd == "top":
                current_rows, chart_type = self._exec_top(args, current_rows)
            elif cmd == "timechart":
                current_rows, chart_type = self._exec_timechart(args, current_rows)

        duration_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        
        # Derive final column list
        columns = []
        if current_rows:
            seen_cols = set()
            for r in current_rows[:20]:
                for k in r.keys():
                    if k not in seen_cols:
                        seen_cols.add(k)
                        columns.append(k)
        else:
            columns = ["_time", "sourcetype", "src", "dest", "action", "signature"]

        return {
            "query": query,
            "execution_time_ms": duration_ms,
            "total_scanned": total_scanned,
            "total_matched": total_matched,
            "result_count": len(current_rows),
            "columns": columns,
            "results": current_rows,
            "chart_type": chart_type,
            "is_aggregated": bool(chart_type)
        }

    def _matches_search(self, search_expr: str, fields: Dict[str, Any]) -> bool:
        """Evaluates whether an event record satisfies the base search expression."""
        if not search_expr or search_expr == "*":
            return True

        # If OR is present, evaluate each disjunction
        if " OR " in search_expr:
            or_parts = search_expr.split(" OR ")
            return any(self._matches_search(part.strip("() "), fields) for part in or_parts if part.strip("() "))

        # Clean outer parentheses
        clean_expr = search_expr.strip("() ")
        tokens = clean_expr.split()

        for tok in tokens:
            tok = tok.strip("() ")
            if not tok or tok.upper() in ("AND", "NOT"):
                continue

            if "=" in tok and "!=" not in tok:
                k, v = tok.split("=", 1)
                k = k.strip().strip("()").lower()
                v = v.strip().strip('"').strip("'").lower()
                val = str(fields.get(k, "")).lower()
                if v == "*":
                    continue
                elif "*" in v:
                    pattern = re.escape(v).replace(r'\*', '.*')
                    if not re.search(f'^{pattern}$', val, flags=re.IGNORECASE):
                        return False
                elif v != val and v not in val:
                    return False
            elif "!=" in tok:
                k, v = tok.split("!=", 1)
                k = k.strip().strip("()").lower()
                v = v.strip().strip('"').strip("'").lower()
                val = str(fields.get(k, "")).lower()
                if v == val:
                    return False
            else:
                kw = tok.strip('"').strip("'").lower()
                if kw.startswith("*") and kw.endswith("*"):
                    kw = kw.strip("*")
                match = any(kw in str(val).lower() for val in fields.values())
                if not match:
                    return False

        return True

    def _exec_stats(self, args: str, rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """Executes | stats agg1(field), agg2(field) by group1, group2"""
        by_fields = []
        aggs = []

        if " by " in args.lower():
            agg_part, by_part = re.split(r'\s+by\s+', args, flags=re.IGNORECASE)
            by_fields = [f.strip() for f in by_part.split(",") if f.strip()]
        else:
            agg_part = args

        # Parse aggregations: count, sum(bytes), avg(latency), max(cpu), values(dest)
        for term in agg_part.split(","):
            term = term.strip()
            m = re.match(r'([a-zA-Z0-9_]+)(?:\(([a-zA-Z0-9_\-\.]+)\))?(?:\s+as\s+([a-zA-Z0-9_]+))?', term, flags=re.IGNORECASE)
            if m:
                func = m.group(1).lower()
                field = m.group(2) or ""
                alias = m.group(3)
                col_name = alias if alias else (f"{func}({field})" if field else func)
                aggs.append((func, field, col_name))

        if not aggs:
            aggs.append(("count", "", "count"))

        groups = defaultdict(list)
        for r in rows:
            if by_fields:
                key = tuple(str(r.get(f, "")) for f in by_fields)
            else:
                key = ("__ALL__",)
            groups[key].append(r)

        result_rows = []
        for key, g_rows in groups.items():
            row_dict = {}
            if by_fields and key != ("__ALL__",):
                for idx, f in enumerate(by_fields):
                    row_dict[f] = key[idx]

            for func, field, col_name in aggs:
                if func == "count":
                    row_dict[col_name] = len(g_rows)
                elif func == "sum":
                    vals = [self._to_num(r.get(field, 0)) for r in g_rows]
                    row_dict[col_name] = round(sum(vals), 2)
                elif func in ("avg", "mean"):
                    vals = [self._to_num(r.get(field, 0)) for r in g_rows]
                    row_dict[col_name] = round(sum(vals) / len(vals), 2) if vals else 0.0
                elif func == "max":
                    vals = [self._to_num(r.get(field, 0)) for r in g_rows]
                    row_dict[col_name] = max(vals) if vals else 0
                elif func == "min":
                    vals = [self._to_num(r.get(field, 0)) for r in g_rows]
                    row_dict[col_name] = min(vals) if vals else 0
                elif func in ("dc", "distinct_count"):
                    distinct_vals = set(str(r.get(field, "")) for r in g_rows)
                    row_dict[col_name] = len(distinct_vals)
                elif func == "values":
                    distinct_vals = sorted(list(set(str(r.get(field, "")) for r in g_rows if r.get(field))))
                    row_dict[col_name] = ", ".join(distinct_vals[:10])

            result_rows.append(row_dict)

        return result_rows, "bar"

    def _exec_where(self, args: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes | where count > 5 or where action == "blocked" """
        res = []
        # Pattern match field op value
        m = re.match(r'([a-zA-Z0-9_\-\.]+)\s*(>=|<=|>|<|==|!=|=)\s*(.+)', args.strip())
        if not m:
            return rows

        field, op, raw_val = m.group(1), m.group(2), m.group(3).strip().strip('"').strip("'")
        num_val = self._to_num(raw_val)

        for r in rows:
            cur_raw = r.get(field, "")
            cur_num = self._to_num(cur_raw)

            match = False
            if op in (">", ">=", "<", "<="):
                if op == ">": match = cur_num > num_val
                elif op == ">=": match = cur_num >= num_val
                elif op == "<": match = cur_num < num_val
                elif op == "<=": match = cur_num <= num_val
            elif op in ("==", "="):
                match = str(cur_raw).lower() == raw_val.lower()
            elif op == "!=":
                match = str(cur_raw).lower() != raw_val.lower()

            if match:
                res.append(r)

        return res

    def _exec_eval(self, args: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes | eval target = expr"""
        if "=" not in args:
            return rows
        target, expr = args.split("=", 1)
        target = target.strip()
        expr = expr.strip()

        for r in rows:
            # Simple division evaluation (e.g. bytes / 1024)
            if "/" in expr:
                p1, p2 = expr.split("/", 1)
                v1 = self._to_num(r.get(p1.strip(), p1.strip()))
                v2 = self._to_num(r.get(p2.strip(), p2.strip()))
                r[target] = round(v1 / v2, 2) if v2 != 0 else 0
            elif "*" in expr:
                p1, p2 = expr.split("*", 1)
                v1 = self._to_num(r.get(p1.strip(), p1.strip()))
                v2 = self._to_num(r.get(p2.strip(), p2.strip()))
                r[target] = round(v1 * v2, 2)
            else:
                # Direct assignment or field copy
                r[target] = r.get(expr, expr.strip('"').strip("'"))

        return rows

    def _exec_table(self, args: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes | table field1, field2, ..."""
        cols = [c.strip() for c in args.split(",") if c.strip()]
        if not cols:
            return rows

        return [{c: r.get(c, "") for c in cols} for r in rows]

    def _exec_sort(self, args: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes | sort -count or | sort +time"""
        parts = args.split()
        if not parts:
            return rows

        target = parts[0]
        reverse = target.startswith("-")
        field = target.lstrip("+-")

        def sort_key(r):
            v = r.get(field, "")
            num = self._to_num(v)
            return num if num != 0 or v == "0" else str(v)

        try:
            return sorted(rows, key=sort_key, reverse=reverse)
        except Exception:
            return rows

    def _exec_top(self, args: str, rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """Executes | top 10 field"""
        parts = args.split()
        limit = 10
        field = parts[0]
        if len(parts) >= 2 and parts[0].isdigit():
            limit = int(parts[0])
            field = parts[1]
        elif len(parts) >= 2 and parts[1].isdigit():
            field = parts[0]
            limit = int(parts[1])

        counts = defaultdict(int)
        for r in rows:
            counts[str(r.get(field, "UNKNOWN"))] += 1

        total = len(rows) or 1
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        top_rows = [
            {field: k, "count": v, "percent": round((v / total) * 100.0, 2)}
            for k, v in sorted_counts
        ]
        return top_rows, "pie"

    def _exec_timechart(self, args: str, rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """Executes | timechart span=5s count by action"""
        # Bucket events into discrete temporal bins
        by_field = ""
        if " by " in args.lower():
            _, by_part = re.split(r'\s+by\s+', args, flags=re.IGNORECASE)
            by_field = by_part.strip()

        bins = defaultdict(lambda: defaultdict(int))
        for r in rows:
            t_str = str(r.get("_time", r.get("timestamp", "")))[:19] or "2026-09-19 14:00:00"
            sub_key = str(r.get(by_field, "count")) if by_field else "count"
            bins[t_str][sub_key] += 1

        chart_rows = []
        for t_bin in sorted(bins.keys()):
            row = {"_time": t_bin}
            row.update(bins[t_bin])
            chart_rows.append(row)

        return chart_rows, "line"

    @staticmethod
    def _to_num(val: Any) -> float:
        """Converts strings/numbers to float safely."""
        if isinstance(val, (int, float)):
            return float(val)
        try:
            s = str(val).strip().rstrip("ms").rstrip("%").rstrip("kbps").rstrip("mbps").rstrip("gbps")
            return float(s)
        except Exception:
            return 0.0


# Global singleton SPL engine
spl_engine = SPLExecutionEngine()