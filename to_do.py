#!/usr/bin/env python3
"""
Simple CLI To-Do List
- Stores tasks in tasks.json in the same folder by default.
- Commands: add, list, done, delete, edit, clear
- Fields: id, text, created_at, due (YYYY-MM-DD), priority (1=high, 3=low), done
"""

from __future__ import annotations
import argparse, json, sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).with_name("tasks.json")

def load_tasks(path: Path = DB_PATH) -> List[Dict[str, Any]]:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []

def save_tasks(tasks: List[Dict[str, Any]], path: Path = DB_PATH) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

def next_id(tasks: List[Dict[str, Any]]) -> int:
    return (max((t["id"] for t in tasks), default=0) + 1)

def parse_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return d.isoformat()
    except ValueError:
        print("Error: --due must be YYYY-MM-DD (e.g., 2025-08-20).", file=sys.stderr)
        sys.exit(2)

def status_symbol(t: Dict[str, Any]) -> str:
    return "✔" if t.get("done") else "•"

def is_overdue(t: Dict[str, Any]) -> bool:
    if t.get("done"): 
        return False
    due = t.get("due")
    if not due:
        return False
    try:
        return date.fromisoformat(due) < date.today()
    except ValueError:
        return False

def add(args):
    tasks = load_tasks()
    task = {
        "id": next_id(tasks),
        "text": args.text.strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "due": parse_date(args.due),
        "priority": args.priority,
        "done": False
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f"Added #{task['id']}: {task['text']}")

def list_cmd(args):
    tasks = load_tasks()

    # Filtering
    if args.done is True:
        tasks = [t for t in tasks if t.get("done")]
    elif args.done is False:
        tasks = [t for t in tasks if not t.get("done")]

    # Sort
    def sort_key(t):
        # done last; then priority asc; then due date (None last); then id
        done_rank = 1 if t.get("done") else 0
        pr = t.get("priority", 3)
        due = t.get("due") or "9999-12-31"
        return (done_rank, pr, due, t["id"])

    tasks.sort(key=sort_key)

    if not tasks:
        print("No tasks found.")
        return

    # Pretty table
    headers = ["ID", "St", "Pri", "Due", "Task"]
    rows = []
    for t in tasks:
        due = t.get("due") or "-"
        if is_overdue(t):
            due = f"{due} (!) "
        rows.append([
            str(t["id"]).rjust(3),
            status_symbol(t),
            str(t.get("priority", 3)),
            due,
            t["text"]
        ])

    # Column widths
    colw = [max(len(h), max(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join("{:<" + str(w) + "}" for w in colw)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in colw]))
    for r in rows:
        print(fmt.format(*r))

def done(args):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == args.id:
            t["done"] = True
            save_tasks(tasks)
            print(f"Marked #{args.id} as done.")
            return
    print(f"Task #{args.id} not found.", file=sys.stderr); sys.exit(1)

def delete(args):
    tasks = load_tasks()
    n_before = len(tasks)
    tasks = [t for t in tasks if t["id"] != args.id]
    if len(tasks) == n_before:
        print(f"Task #{args.id} not found.", file=sys.stderr); sys.exit(1)
    save_tasks(tasks)
    print(f"Deleted #{args.id}.")

def edit(args):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == args.id:
            if args.text is not None:
                t["text"] = args.text.strip()
            if args.due is not None:
                t["due"] = parse_date(args.due)
            if args.priority is not None:
                t["priority"] = args.priority
            save_tasks(tasks)
            print(f"Updated #{args.id}.")
            return
    print(f"Task #{args.id} not found.", file=sys.stderr); sys.exit(1)

def clear(args):
    tasks = load_tasks()
    if args.done:
        tasks = [t for t in tasks if not t.get("done")]
        save_tasks(tasks)
        print("Cleared all completed tasks.")
    elif args.all:
        save_tasks([])
        print("Cleared all tasks.")
    else:
        print("Specify --done or --all", file=sys.stderr); sys.exit(2)

def build_parser():
    p = argparse.ArgumentParser(prog="todo", description="Simple To-Do CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # add
    pa = sub.add_parser("add", help="Add a task")
    pa.add_argument("text", help="Task description in quotes")
    pa.add_argument("--due", help="Due date YYYY-MM-DD")
    pa.add_argument("--priority", type=int, choices=[1,2,3], default=3,
                    help="1=high, 2=med, 3=low (default 3)")
    pa.set_defaults(func=add)

    # list
    pl = sub.add_parser("list", help="List tasks")
    g = pl.add_mutually_exclusive_group()
    g.add_argument("--done", dest="done", action="store_true", help="Only completed")
    g.add_argument("--todo", dest="done", action="store_false", help="Only pending")
    pl.set_defaults(func=list_cmd)

    # done
    pd = sub.add_parser("done", help="Mark a task as done")
    pd.add_argument("id", type=int)
    pd.set_defaults(func=done)

    # delete
    pdel = sub.add_parser("delete", help="Delete a task")
    pdel.add_argument("id", type=int)
    pdel.set_defaults(func=delete)

    # edit
    pe = sub.add_parser("edit", help="Edit task text/due/priority")
    pe.add_argument("id", type=int)
    pe.add_argument("--text")
    pe.add_argument("--due")
    pe.add_argument("--priority", type=int, choices=[1,2,3])
    pe.set_defaults(func=edit)

    # clear
    pc = sub.add_parser("clear", help="Clear tasks")
    g2 = pc.add_mutually_exclusive_group(required=True)
    g2.add_argument("--done", action="store_true", help="Remove completed tasks")
    g2.add_argument("--all", action="store_true", help="Remove all tasks")
    pc.set_defaults(func=clear)

    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
