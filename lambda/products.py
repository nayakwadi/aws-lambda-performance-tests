"""
Products CRUD handler for the API Gateway -> Lambda -> DynamoDB performance lab.

A single Lambda handler backs all five REST routes. API Gateway (REST API with
Lambda proxy integration) passes the HTTP method and path parameters in `event`,
and this handler dispatches to the right DynamoDB operation.

Routes:
    POST   /products          -> create
    GET    /products          -> list (scan)
    GET    /products/{id}     -> read one
    PUT    /products/{id}     -> update
    DELETE /products/{id}     -> delete

The table name is injected via the TABLE_NAME environment variable by CDK, so the
same code runs unchanged across the 128MB / 512MB / 1024MB memory variants used
for performance comparison.
"""

import json
import os
import time
import uuid
from decimal import Decimal

import boto3

# Reuse the client across warm invocations. Creating it at module scope (outside
# the handler) is the single most important cold-start optimisation here: the
# connection and credential setup happen once per execution environment, not once
# per request.
TABLE_NAME = os.environ.get("TABLE_NAME", "Products")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns numbers as Decimal; make them JSON-serialisable."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            # Render whole numbers as int, the rest as float.
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def _now_ms():
    return int(time.time() * 1000)


def create(body):
    item = {
        "id": body.get("id") or str(uuid.uuid4()),
        "name": body["name"],
        "category": body.get("category", "uncategorized"),
        "price": Decimal(str(body.get("price", 0))),
        "stock": int(body.get("stock", 0)),
        "createdAt": _now_ms(),
    }
    table.put_item(Item=item)
    return _response(201, item)


def read(product_id):
    result = table.get_item(Key={"id": product_id})
    item = result.get("Item")
    if not item:
        return _response(404, {"message": f"Product {product_id} not found"})
    return _response(200, item)


def list_all():
    # Scan is intentionally used here: it is the most memory-/CPU-sensitive
    # operation, which makes it the best route to highlight in a Lambda memory
    # tuning comparison.
    result = table.scan()
    items = result.get("Items", [])
    return _response(200, {"count": len(items), "items": items})


def update(product_id, body):
    existing = table.get_item(Key={"id": product_id}).get("Item")
    if not existing:
        return _response(404, {"message": f"Product {product_id} not found"})

    expr_parts, names, values = [], {}, {}
    for field in ("name", "category", "price", "stock"):
        if field in body:
            expr_parts.append(f"#{field} = :{field}")
            names[f"#{field}"] = field
            val = body[field]
            values[f":{field}"] = Decimal(str(val)) if field == "price" else val

    if not expr_parts:
        return _response(400, {"message": "No updatable fields supplied"})

    table.update_item(
        Key={"id": product_id},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )
    return read(product_id)


def delete(product_id):
    existing = table.get_item(Key={"id": product_id}).get("Item")
    if not existing:
        return _response(404, {"message": f"Product {product_id} not found"})
    table.delete_item(Key={"id": product_id})
    return _response(200, {"message": f"Product {product_id} deleted"})


def lambda_handler(event, context):
    method = event.get("httpMethod")
    path_params = event.get("pathParameters") or {}
    product_id = path_params.get("id")

    raw_body = event.get("body")
    body = {}
    if raw_body:
        try:
            body = json.loads(raw_body)
        except (TypeError, json.JSONDecodeError):
            return _response(400, {"message": "Request body must be valid JSON"})

    try:
        if method == "POST" and not product_id:
            if "name" not in body:
                return _response(400, {"message": "Field 'name' is required"})
            return create(body)
        if method == "GET" and product_id:
            return read(product_id)
        if method == "GET":
            return list_all()
        if method == "PUT" and product_id:
            return update(product_id, body)
        if method == "DELETE" and product_id:
            return delete(product_id)
        return _response(405, {"message": f"Unsupported route: {method} {event.get('resource')}"})
    except KeyError as exc:
        return _response(400, {"message": f"Missing required field: {exc}"})
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors as 500
        return _response(500, {"message": "Internal error", "detail": str(exc)})
