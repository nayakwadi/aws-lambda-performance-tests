#!/usr/bin/env python3
"""CDK app entry point for the Products performance lab."""

import aws_cdk as cdk

from products_perf.products_perf_stack import ProductsPerfStack

app = cdk.App()

ProductsPerfStack(
    app,
    "ProductsPerfStack",
    description="API Gateway -> Lambda -> DynamoDB Products CRUD lab for Lambda performance tuning",
)

app.synth()
