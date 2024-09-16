# pylint: disable=no-member
import asyncio
import json
import nats
from langchain.tools import BaseTool
from toolgate.logging import logger
import toolgate.generated.proto.v1.service_pb2 as service_pb2


class ToolService:
    """Concrete ToolGate service tool implementation."""

    def __init__(self, client: nats.NATS, tool: BaseTool, prefix: str = None):
        self.client = client
        self.tool = tool
        self.prefix = prefix
        self.nc = None

    def serve(self):
        """Serve the tool by subscribing to the NATS server."""
        asyncio.run(self.a_serve())

    async def a_serve(self):
        """Serve the tool by subscribing to the NATS server."""
        self.nc = await self.client.connect()
        await self.subscribe()

    async def subscribe(self):
        """Subscribe to the service subject and run handlers."""

        async def _info_handler(msg):
            logger.info("Running tool handler %s", self.tool.name)
            response = service_pb2.ServiceResponse()
            response.meta.subject = self.subject()
            response.meta.handler = service_pb2.Handler.GET
            response.meta.puppet = service_pb2.Puppet.LANGCHAIN_TOOL
            response.puppet_response.lc_tool.name = self.tool.name
            response.puppet_response.lc_tool.description = self.tool.description
            response.puppet_response.lc_tool.args_schema = json.dumps(
                self.tool.args_schema.schema()
            )

            await self.nc.publish(msg.reply, response.SerializeToString())

        async def _run_handler(msg, query: str = None):
            logger.info("Running tool %s with query: %s", self.tool.name, query)
            response = service_pb2.ServiceResponse()
            response.meta.subject = self.subject()
            response.meta.handler = service_pb2.Handler.RUN
            response.meta.puppet = service_pb2.Puppet.LANGCHAIN_TOOL

            response.puppet_response.lc_tool.result = self.tool.run(
                tool_input=json.loads(query)
            )

            await self.nc.publish(msg.reply, response.SerializeToString())

        async def _main_handler(msg):
            logger.debug("Running main handler for message: %s", msg.data)
            request = service_pb2.ServiceRequest()
            request.ParseFromString(msg.data)
            if request.IsInitialized():
                if (
                    request.meta.subject == self.subject()
                    and request.meta.handler == service_pb2.Handler.GET
                    and request.meta.puppet == service_pb2.Puppet.LANGCHAIN_TOOL
                ):
                    await _info_handler(msg)
                elif (
                    request.meta.subject == self.subject()
                    and request.meta.handler == service_pb2.Handler.RUN
                    and request.meta.puppet == service_pb2.Puppet.LANGCHAIN_TOOL
                ):
                    await _run_handler(msg, query=request.puppet_request.lc_tool.query)

        sub = await self.nc.subscribe(self.subject(), cb=_main_handler)

        if sub:
            logger.info("Tool %s got subscribed to %s", self.tool.name, sub.subject)
        while True:
            await asyncio.sleep(10)

    def subject(self) -> str:
        """Return the subject for the tool."""

        return self.prefix + "." + self.tool.name

    def tool_metadata_dict(self):
        """Return a dictionary representation of the tool metadata."""

        return {
            "name": self.tool.name,
            "description": self.tool.description,
            "args_schema": (
                self.tool.args_schema.schema() if self.tool.args_schema else None
            ),
        }
