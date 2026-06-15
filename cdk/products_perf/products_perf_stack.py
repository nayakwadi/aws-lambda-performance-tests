"""
ProductsPerfStack
=================

Defines the whole lab in one CDK stack:

  * A DynamoDB table `Products` (on-demand billing, partition key `id`).
  * THREE Lambda functions running identical code, differing only in memory:
        - ProductsFn128   (128 MB)
        - ProductsFn512   (512 MB)
        - ProductsFn1024  (1024 MB)
    Having three side-by-side functions lets you compare memory tiers in Postman
    without redeploying between runs.
  * A REST API Gateway exposing proper CRUD routes, with one stage *per memory
    tier* so each tier has its own base URL:
        /prod-128/products ...
        /prod-512/products ...
        /prod-1024/products ...

Everything is destroyable with `cdk destroy` (the table has RemovalPolicy.DESTROY),
so cleanup is a single command and you are not left paying for stray resources.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct

MEMORY_TIERS = [128, 512, 1024]


class ProductsPerfStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---- DynamoDB -----------------------------------------------------
        table = dynamodb.Table(
            self,
            "ProductsTable",
            table_name="Products",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # lab resource -> easy cleanup
        )

        # ---- One Lambda + one API stage per memory tier -------------------
        for mem in MEMORY_TIERS:
            fn = _lambda.Function(
                self,
                f"ProductsFn{mem}",
                function_name=f"products-crud-{mem}mb",
                runtime=_lambda.Runtime.PYTHON_3_13,
                handler="products.lambda_handler",
                code=_lambda.Code.from_asset("../lambda"),
                memory_size=mem,
                timeout=Duration.seconds(15),
                environment={"TABLE_NAME": table.table_name},
                description=f"Products CRUD handler @ {mem}MB",
            )
            table.grant_read_write_data(fn)

            api = apigw.RestApi(
                self,
                f"ProductsApi{mem}",
                rest_api_name=f"products-api-{mem}mb",
                description=f"Products CRUD REST API backed by the {mem}MB Lambda",
                deploy_options=apigw.StageOptions(stage_name=f"prod-{mem}"),
                default_cors_preflight_options=apigw.CorsOptions(
                    allow_origins=apigw.Cors.ALL_ORIGINS,
                    allow_methods=apigw.Cors.ALL_METHODS,
                ),
            )

            integration = apigw.LambdaIntegration(fn, proxy=True)

            # /products  -> list (GET), create (POST)
            products = api.root.add_resource("products")
            products.add_method("GET", integration)
            products.add_method("POST", integration)

            # /products/{id} -> read (GET), update (PUT), delete (DELETE)
            product = products.add_resource("{id}")
            product.add_method("GET", integration)
            product.add_method("PUT", integration)
            product.add_method("DELETE", integration)

            CfnOutput(
                self,
                f"ApiUrl{mem}MB",
                value=api.url,
                description=f"Base URL for the {mem}MB tier (append 'products')",
            )

        CfnOutput(self, "TableNameOut", value=table.table_name)
