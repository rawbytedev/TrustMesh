import os, asyncio, json
from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI
from core import ArcHandler, BatchRunner, Cache, EscrowType, Storage, TimerScheduler
from tools import make_tools

# --- Load system prompt from file ---
def load_config(path="config.json"):
    with open(path) as f:
        cfg = json.load(f)
    for key, value in cfg.items():
        os.environ[key] = str(value)

load_config()
with open("prompts/system_prompt.txt") as f:
    system_prompt = f.read()

prompt = system_prompt

# --- Model initialization ---
model = ChatMistralAI(
    model_name=os.getenv("MODEL_NAME", "mistral-medium"),
    api_key=os.getenv("MODEL_API_KEY"),
    temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1")),
    max_tokens=int(os.getenv("MODEL_MAX_TOKENS", "8000")),
)
provider_url = os.getenv("CHAIN_URL", "127.0.0.1")
contract_address = os.getenv("CONTRACT_ADDRESS")
agent_key = os.getenv("AGENT_KEY", "0x0")

with open("./trustmesh.json") as f:
    abi = json.load(f)

# --- Main orchestrator ---
async def main():
    cache = Cache()
    storage = Storage(cache=cache)
    timer = TimerScheduler()
    arc = ArcHandler(provider_url, contract_address, abi, agent_key, storage)
    batch_runner = BatchRunner(cache)

    tools = make_tools(arc, storage, timer)

    # build agent with these tools
    agent = create_agent(model, tools, system_prompt=prompt)
    executor = agent
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
    async def timer_callback(entry):
        escrow_info = {
            "escrow_id":entry.escrow_id,
            "reason": entry.reason,
            "attempts": entry.attempts,
            "due_at": entry.due_at,
        }
        await executor.ainvoke({"input":f"Set timer elasped: {json.dumps(escrow_info)}"})
        pass
    await asyncio.gather(
        arc.listen_events(),  # event listener runs
        timer.run(timer_callback),
        batch_runner.run(ai_callback)
    )

if __name__ == "__main__":
    asyncio.run(main())