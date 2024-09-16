"""Client module for the toolgate client."""

from typing import List, Union, Optional, Any, Dict
import threading
import nats
from nats.errors import (
    ConnectionClosedError,
    NoServersError,
    TimeoutError as NatsTimeoutError,
)

from langchain.tools import BaseTool

from toolgate.logging import logger
from toolgate.langchain.services import ToolService


class Client:
    """Client class is the facade for the toolgate client."""

    nats_servers: Union[str, List[str]] = ["nats://localhost:4222"]
    nats_options: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        nats_servers: Union[str, List[str]] = None,
        nats_options: Optional[Dict[str, Any]] = None,
    ):
        self.nats_servers = nats_servers or self.nats_servers
        self.nats_options = nats_options or self.nats_options

    async def connect(self) -> nats.NATS:
        """Connect to the NATS server."""
        try:
            logger.info("Creating new NATS connection")
            nc = None
            nc = await nats.connect(
                servers=self.nats_servers, **self.nats_options or {}
            )
            logger.info("Connected to NATS server: %s", nc.connected_url.netloc)

            return nc
        except (ConnectionClosedError, NatsTimeoutError, NoServersError) as e:
            logger.error("Error connecting to NATS server: %s", e)
            await nc.close()
            logger.info("Closed NATS connection")

    def run_service(self, runnable: BaseTool, prefix: Optional[str] = None):
        """Run the service for the tool."""

        if not isinstance(runnable, BaseTool):
            raise TypeError(
                f"Expected runnable to be an instance of BaseTool, got {type(runnable).__name__} instead"
            )

        ts = ToolService(client=self, tool=runnable, prefix=prefix)

        ts_thread = threading.Thread(target=ts.serve)
        ts_thread.start()

        return ts_thread