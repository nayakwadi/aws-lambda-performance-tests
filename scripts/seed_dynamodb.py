#!/usr/bin/env python3
"""
Bulk-load mock products into the DynamoDB `Products` table.

Usage:
    python scripts/seed_dynamodb.py                 # loads data/products.json
    python scripts/seed_dynamodb.py --table Products --region us-east-1
    python scripts/seed_dynamodb.py --clear         # delete all items first

Requires AWS credentials in your environment (same ones the CDK deploy uses).
The script uses batch_writer() so 200 items load in a handful of round-trips,
which is plenty of data to make a Lambda `list`/scan show measurable differences
across memory tiers.
"""

import argparse
import json
import os
from decimal import Decimal

import boto3

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "..", "data", "products.json")


def load_items(path):
    with open(path) as fh:
        raw = json.load(fh)
    # DynamoDB needs Decimal, not float, for numeric attributes.
    for item in raw:
        item["price"] = Decimal(str(item["price"]))
        item["stock"] = int(item["stock"])
    return raw


def clear_table(table):
    scanned = table.scan(ProjectionExpression="id").get("Items", [])
    with table.batch_writer() as batch:
        for item in scanned:
            batch.delete_item(Key={"id": item["id"]})
    print(f"Cleared {len(scanned)} existing items.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="Products")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument("--data", default=DEFAULT_DATA)
    parser.add_argument("--clear", action="store_true", help="Delete all items before loading")
    args = parser.parse_args()

    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)

    if args.clear:
        clear_table(table)

    items = load_items(args.data)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    print(f"Seeded {len(items)} products into '{args.table}' ({args.region}).")


if __name__ == "__main__":
    main()
