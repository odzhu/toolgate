#! /usr/bin/env python3

"""
Example Toolgate service for running LangChain tools remotely.

For more details on LangChain custom tools development see: 
https://python.langchain.com/v0.1/docs/modules/tools/custom_tools/
"""

from typing import Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from toolgate.client import Client

class WeatherInput(BaseModel):
    """ Weather Tool Input Args Schema."""
    period: str = Field(None, description="Input period for weather information.")

class WeatherTool(BaseTool):
    """
    Weather Tool class.
    """
    name: str = "Weather"
    description: str = "Provides weather information on particular date."
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, period: str = None) -> str:
        """Run the tool."""
        return f"Weather is sunny during {period}."


def main():
    """Main function to run your toolgate service."""

    wt = WeatherTool()

    #Create ToolGate client
    client = Client(nats_servers=["nats://localhost:4222"])

    #Run the service for the tool
    thread = client.run_service(runnable=wt, prefix="default")

    #Wait for the service
    thread.join()


main()
