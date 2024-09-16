# pylint: disable=no-member

import asyncio
from typing import Dict
import json
from pydantic import BaseModel, create_model
from langchain.tools import BaseTool
from toolgate.client import Client

from toolgate.logging import logger
import toolgate.generated.proto.v1.service_pb2 as service_pb2


class ToolConsumer(BaseTool):
    """Concrete ToolGate consumer tool implementation."""

    name: str = None
    description: str = None
    args_schema: BaseModel = None

    subject: str = None
    client: Client = None

    constructed: bool = False

    def __init__(self, client: Client, subject: str = None):
        super().__init__()
        self.subject = subject
        self.client = client
        asyncio.run(self.construct())

    async def construct(self):
        """Construct the tool by requesting metadata from the service."""
        nc = await self.client.connect()

        request = service_pb2.ServiceRequest()
        request.meta.subject = self.subject
        request.meta.puppet = service_pb2.Puppet.LANGCHAIN_TOOL
        request.meta.handler = service_pb2.Handler.GET

        if request.IsInitialized():
            logger.info("Consumer construct request is initialized to subject %s", self.subject)
            reply = await nc.request(
                self.subject, request.SerializeToString(), timeout=0.5
            )
            response = service_pb2.ServiceResponse()
            response.ParseFromString(reply.data)

            if response.IsInitialized():
                logger.info("Subject %s response is validated", self.subject)

            self.name = response.puppet_response.lc_tool.name
            self.description = response.puppet_response.lc_tool.description
            self.args_schema = (
                self.model_args(
                    json.loads(response.puppet_response.lc_tool.args_schema)
                )
                if response.puppet_response.lc_tool.args_schema
                else None
            )
            self.constructed = True and logger.info("Consumer is ready for tool %s using subject %s", self.name, self.subject)

    def _run(self, *args, **kwargs) -> str:
        """Run the tool with the provided arguments."""

        tool_input = {}
        tool_input.update(kwargs)
        tool_input["args"] = list(args)

        logger.info("Running consumer %s with input: %s", self.name, tool_input)

        return asyncio.run(self.run_request(tool_input))

    async def run_request(self, tool_input: Dict) -> str:
        """Request a tool run from the service."""
        nc = await self.client.connect()

        logger.info("Consumer tool %s is requesting subject %s", self.name, self.subject)

        request = service_pb2.ServiceRequest()
        request.meta.subject = self.subject
        request.meta.puppet = service_pb2.Puppet.LANGCHAIN_TOOL
        request.meta.handler = service_pb2.Handler.RUN
        request.puppet_request.lc_tool.query = json.dumps(tool_input)

        if request.IsInitialized():
            logger.debug("Run request is initialized")

        reply = await nc.request(self.subject, request.SerializeToString(), timeout=0.5)

        response = service_pb2.ServiceResponse()
        response.ParseFromString(reply.data)

        if response.IsInitialized():
            logger.info("Consumer tool %s got and validated response from subject %s for run request", self.name, self.subject)
            return response.puppet_response.lc_tool.result
        return "Run response is not initialized"

    def model_args(self, schema: Dict[str, str]) -> BaseModel:
        """Create a Pydantic model based on the provided schema."""

        name = schema["title"]
        properties = schema["properties"]

        type_mapping = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "number": float,
            "array": list,
            "object": dict,
        }

        fields = {
            prop_name: (
                type_mapping[prop_info["type"]],
                str(prop_info) if "description" in prop_info else None,
            )
            for prop_name, prop_info in properties.items()
        }

        model = create_model(name, **fields)
        return model
