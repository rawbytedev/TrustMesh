from locale import getencoding
import os
from typing import Sequence
from langchain.llms.openai import OpenAIChat
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain.agents import initialize_agent, AgentType
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools import get_escrow_state, refund_funds,release_funds

tools = get_escrow_state, refund_funds, release_funds
prompt = ChatPromptTemplate.from_messages([
    ("system",
    f"""You are an agent who was given a set of tools use those accuratly to peform actions"""
)]
)
model = init_chat_model(
        model=os.getenv("MODEL_NAME", "gpt-4.1"),
        model_provider=os.getenv("MODEL_PROVIDER", "openai"),
        api_key=os.getenv("MODEL_API_KEY"),
        temperature=os.getenv("MODEL_TEMPERATURE", "0.1"),
        max_tokens=os.getenv("MODEL_MAX_TOKENS", "8000"),
        base_url=os.getenv("MODEL_BASE_URL", None)
    )
agent = create_tool_calling_agent(model, tools, prompt=prompt)
llm = OpenAIChat(
    temperature=0,
    model="gpt-4o-mini",  # or whichever model you want
    api_key=os.getenv("MODEL_API_KEY")
)
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)
"""
"""