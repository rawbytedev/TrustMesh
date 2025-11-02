import os, asyncio, json
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from core import ArcHandler, BatchRunner, Cache, EscrowType, Storage, TimerScheduler
from tools import make_tools


# --- Load system prompt from file ---

with open("prompts/system_prompt.txt") as f:
    system_prompt = f.read()

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt)
])

# --- Model initialization ---
model = init_chat_model(
    model=os.getenv("MODEL_NAME", "gpt-4.1"),
    model_provider=os.getenv("MODEL_PROVIDER", "openai"),
    api_key=os.getenv("MODEL_API_KEY"),
    temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1")),
    max_tokens=int(os.getenv("MODEL_MAX_TOKENS", "8000")),
    base_url=os.getenv("MODEL_BASE_URL", None)
)



# --- Main orchestrator ---
async def main():
    storage = Storage()
    timer = TimerScheduler()
    arc = ArcHandler(provider_url, contract_address, abi, agent_key, storage)
    cache = Cache()
    batch_runner = BatchRunner(cache)

    tools = make_tools(arc, storage, timer)

    # build agent with these tools
    agent = create_tool_calling_agent(model, tools, prompt=prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    # --- AI callback for BatchRunner ---
    async def ai_callback(batch):
        for e in batch:
            escrow_info = {
            "escrow_id": e.escrow_id,
            "etype": e.etype.name,
            "seen_count": e.seen_count,
            }
            await executor.ainvoke({
            "input": f"Process escrow event: {json.dumps(escrow_info)}"
            })
    await asyncio.gather(
        arc.listen_events(),  # event listener runs
        timer.run(lambda entry: cache.add(entry.escrow_id, EscrowType.LINKED)),
        batch_runner.run(ai_callback)
    )
