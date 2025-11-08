import os, asyncio, json
import signal
from typing import List
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from core import ArcHandler, BatchRunner, Cache, EscrowRef, EscrowType, Storage, TimerScheduler
from tools import make_tools
import logging
from logging_setup import setup_logging, shutdown_logging
from async_utils import create_monitored_task, set_loop_exception_handler
# --- Logging configuration ---
setup_logging()
set_loop_exception_handler(asyncio.get_event_loop())
log = logging.getLogger(__name__)
# --- Load system prompt from file ---
log.info("Loading configurations")
def load_config(path="config.json"):
    with open(path) as f:
        cfg = json.load(f)
    for key, value in cfg.items():
        os.environ[key] = str(value)

#load_config()
with open("prompts/system_prompt.txt") as f:
    system_prompt = f.read()


prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "{input}"),
    ("assistant", "{agent_scratchpad}")
])

log.info("Starting TrustMesh Server...")
# --- Model initialization ---
log.info("Initializing AI Model")
model = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "gpt-4.1-nano"),
    api_key=os.getenv("MODEL_API_KEY"),
    temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1")))
provider_url = os.getenv("CHAIN_URL", "127.0.0.1")
contract_address = os.getenv("CONTRACT_ADDRESS")
agent_key = os.getenv("AGENT_KEY", "0x0")

with open("./trustmesh.json") as f:
    abi = json.load(f)
# --- Mapping prefixes to EscrowType ---
PREFIX_TO_ETYPE = {
    "rf": EscrowType.REFUNDED,
    "rl": EscrowType.RELEASED,
    "xp": EscrowType.EXPIRED,
    "ex": EscrowType.EXTENDED,
    "lk": EscrowType.LINKED,
    "cn": EscrowType.CANCELLED,
    "ec": EscrowType.CREATED,
}

# --- Main orchestrator ---
async def _main():
    
    log.info("Initializing components")
    cache = Cache()
    log.info("Cache initialized")
    storage = Storage(cache=cache)
    log.info("Storage initialized")
    timer = TimerScheduler()
    log.info("TimerScheduler initialized")
    arc = ArcHandler(provider_url, contract_address, abi, agent_key, storage)
    log.info("ArcHandler initialized")
    batch_runner = BatchRunner(cache, interval=10)
    log.info("BatchRunner initialized")

    tools = make_tools(arc, storage, timer)
    model.bind_tools(tools)
    log.info("Tools created and bound to model")
    # build agent with these tools
    log.info("Building agent")
    model.bind_tools(tools)
    agent = create_agent(model=model, tools=tools,system_prompt=system_prompt, debug=True)
    executor = agent
    log.info("AgentExecutor initialized")
    # --- AI callback for BatchRunner ---
    async def ai_callback(batch):
        for e in batch:
            escrow_info = {
            "escrow_id": e.escrow_id,
            "etype": e.etype.name,
            "seen_count": e.seen_count,
            }
            #await toolsbase["get_escrow_by_id"].coroutine(e.escrow_id)
            try:
                await executor.ainvoke(
                {"messages": [{"role": "user", "content": f"Process escrow event: {json.dumps(escrow_info)}"}]})
            except Exception as e:
                log.error(f"ai_callback: {e}")
                log.warning("Falling back to manual handling")
                await ai_fallback(batch)
        

    async def timer_callback(entry):
        escrow_info = {
            "escrow_id":entry.escrow_id,
            "reason": entry.reason,
            "attempts": entry.attempt,
            "due_at": entry.due_at,
        }
        
        try:
            await executor.ainvoke({
            "messages": [{"role": "user", "content": f"Set timer elapsed: {json.dumps(escrow_info)}"}]
        })
        except Exception as e:
                log.error(f"timer_callback: {e}")
                log.warning("Falling back to manual handling")
                batch:List[EscrowRef] = []
                 # reconstruct EscrowRef
                prefix, data = await toolsbase["get_escrow_by_id"].coroutine(entry.escrow_id)
                etype = PREFIX_TO_ETYPE.get(prefix, EscrowType.CREATED)
                
                ref = EscrowRef(
                escrow_id=entry.escrow_id,
                etype=etype,
                first_seen_at=entry.due_at,
                last_seen_at=entry.due_at,
                seen_count=entry.attempt,
                )
                # reuse ai_callback fallback
                await ai_fallback([ref], send=1)
        

    async def test_ai():
        log.info("Running test AI invocation")
        response = await executor.ainvoke({
            "messages": [{"role": "user", "content": "Hello, TrustMesh!"}]
        })
        log.info(f"Test AI response: {response}")
    toolsbase = {t.name: t for t in tools} 
    
    async def ai_fallback(batch, send:int=None):
        for e in batch:
            ## possibly extensible
            escrow_info = {
            "escrow_id": e.escrow_id,
            "etype": e.etype,
            "seen_count": e.seen_count,
            }
            try:
                if e.etype.name in ['EXPIRED']:
                    log.warning(f"ai_fallback refunding {e.escrow_id} escrow expired")
                    await toolsbase["finalize_expired_refund"].coroutine(e.escrow_id, "escrow expired")
                else:
                    log.info(f"ai_fallback: retrieving escrow details from storage")
                    prefix,_details = await toolsbase["get_escrow_by_id"].coroutine(e.escrow_id)
                    etype = PREFIX_TO_ETYPE.get(prefix, EscrowType.CREATED)
                    details = json.loads(_details)
                    if e.escrow_id == details["escrowId"]: ## sec check
                        log.info(f"ai_fallback: requesting shipment details for {details["shipmentId"]}")
                        status = await toolsbase["query_shipment"].coroutine(details["shipmentId"])
                        log.info(f"ai_fallback: status of {e.escrow_id} is {status["details"][0]['status']}")
                        state = status["details"][0]['status'] # [0] we are dealing with a list of details ##support for batching soon
                        if state.upper() == "DELIVERED": # we trust feed server
                            if etype.name in ['LINKED']:
                                # demo 15s
                                await toolsbase["extend_escrow"].coroutine(e.escrow_id, 15, "hold period")
                            elif etype.name in ['EXTENDED']:
                                # no complain from buyer at this point
                                try:
                                    if send: ## ensure only release is trigger by timer (make sure hold period is respected)
                                        await toolsbase['release_funds'].coroutine(e.escrow_id, "no complain from user and hold period passed")
                                    else:
                                        await toolsbase["set_timer"].coroutine(e.escrow_id, 45, "release funds")
                                except Exception:
                                    log.fatal(f"Error while releasing funds for {e.escrow_id}")
                                    await toolsbase["set_timer"].coroutine(e.escrow_id, 10,"rescheduling release")
                            ## unlikely to reach here but in case
                            else:
                                log.fatal(f"Reached wrong section with {escrow_info}")
                        elif state.upper() == "IN-TRANSIT":
                            ## demo 10s
                            if send:
                                await toolsbase["set_timer"].coroutine(e.escrow_id, 5, "shipment still in Transit")
                        elif state.upper().__contains__("DELAY"):
                            ## demo 15s
                            await toolsbase["set_timer"].coroutine(e.escrow_id, 10, "shipment face a certain delay")
                        elif state.upper().__contains__("ANOMALY"):
                            await toolsbase["refund_funds"].coroutine(e.escrow_id, "Scamming(Fraud) detected refunding")
                        else:
                            await toolsbase["set_timer"].coroutine(e.escrow_id, 5, "waiting for more details")
            except Exception as ex:
                log.error(f"ai_fallback processing {escrow_info['escrow_id']}: {ex}", exc_info=True)
    # --- Run main tasks ---
    tasks = [
        #create_monitored_task(test_ai()),  # test AI invocation
        create_monitored_task(arc.listen_events()),  # event listener runs
        create_monitored_task(timer.run(timer_callback)),
        create_monitored_task(batch_runner.run(ai_callback))
    ]
    stop = asyncio.Event()
    def _on_signal():
        log.info("Shutdown signal received")
        stop.set()

    for s in (signal.SIGINT, signal.SIGTERM):
       signal.signal(s, lambda sig, frame: _on_signal())

    await stop.wait()
    log.info("Stopping task...")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("Shutdown complete")

def main():
    try:
        asyncio.run(_main())
    finally:
        shutdown_logging()

if __name__ == "__main__":
    main()