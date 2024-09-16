"""Sample Strweamlit app which is using remote langchain tool."""

import os
from langchain.agents import AgentType, initialize_agent
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_openai import ChatOpenAI, AzureChatOpenAI
import streamlit

from toolgate.client import Client
from toolgate.langchain.consumers import ToolConsumer


def main():
    """Main function to run the Streamlit app."""

    # Create ToolGate client
    client = Client(nats_servers=["nats://localhost:4222"])

    # Create ToolConsumer which mimics remote tool and is a usual langchain tool!
    consumer = ToolConsumer(client=client, subject="default.Weather")

    if os.environ.get("OPENAI_API_TYPE") == "azure":
        llm = AzureChatOpenAI(model="gpt-4", temperature=0)
    else:
        llm = ChatOpenAI(model="gpt-4", temperature=0)

    agent_executor = initialize_agent(
        tools=[consumer],
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        handle_parsing_errors=True,
        verbose=False,
    )

    streamlit_callback = StreamlitCallbackHandler(streamlit.container())

    if prompt := streamlit.chat_input():
        streamlit.chat_message("user").write(prompt)
        with streamlit.chat_message("assistant"):
            streamlit_callback = StreamlitCallbackHandler(streamlit.container())
            response = agent_executor.run(prompt, callbacks=[streamlit_callback])
            streamlit.write(response)


main()
