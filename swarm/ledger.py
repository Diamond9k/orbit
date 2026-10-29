"""The fleet ledger is a Markdown table, one row per piece of work."""

import argparse
import os
import sys
from datetime import datetime

HEADER = "| date | task | worker | minutes | result | note |\n|---|---|---|---|---|---|\n"

def add(path, task, worker, minutes, result, note, date=None):
    if result not in ("accepted", "failed"):
        raise ValueError("result must be 'accepted' or 'failed'")
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
    note = note.replace("|", "\\|")
    row = f"| {date} | {task} | {worker} | {minutes} | {result} | {note} |\n"
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(HEADER)
    with open(path, "a", encoding="utf-8") as f:
        f.write(row)

def totals(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    data = {}
    for line in lines[2:]:
        parts = line.strip().split(" | ")
        worker = parts[2]
        minutes = int(parts[3])
        result = parts[4]
        if worker not in data:
            data[worker] = {"rows": 0, "minutes": 0, "accepted": 0, "failed": 0}
        data[worker]["rows"] += 1
        data[worker]["minutes"] += minutes
        if result == "accepted":
            data[worker]["accepted"] += 1
        elif result == "failed":
            data[worker]["failed"] += 1
    return data

def main(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--file", required=True)
    add_parser.add_argument("--task", required=True)
    add_parser.add_argument("--worker", required=True)
    add_parser.add_argument("--minutes", type=int, required=True)
    add_parser.add_argument("--result", required=True)
    add_parser.add_argument("--note", default="")
    add_parser.add_argument("--date", default=None)
    
    sum_parser = subparsers.add_parser("sum")
    sum_parser.add_argument("--file", required=True)
    
    args = parser.parse_args(argv)
    
    if args.command == "add":
        add(args.file, args.task, args.worker, args.minutes, args.result, args.note, args.date)
        return 0
    elif args.command == "sum":
        totals_data = totals(args.file)
        for worker, stats in totals_data.items():
            print(f"{worker}: {stats['rows']} rows, {stats['minutes']} minutes, {stats['accepted']} accepted, {stats['failed']} failed")
        return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
