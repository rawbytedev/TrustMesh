import base64
import json
import time
from web3 import Web3
from web3._utils.events import get_event_data
from web3.contract import Contract

URL = "http://127.0.0.1:8545/"

w3 = Web3(Web3.HTTPProvider(URL))


def generateConfigAddress(path: str = "ConfigKeys.txt"):
    agent = w3.eth.account.create()
    owner = w3.eth.account.create()
    print(f"agent_address: {agent.address}")
    print(f"owner_address: {owner.address}")
    with open(path, "w") as f:
        f.write("=== TrustMesh Config ===\n")
        f.write(f"agent_address: {agent.address}\n")
        f.write(f"agent_priv_key_b64: {agent.key.hex()}\n")
        f.write(f"owner_address: {owner.address}\n")
        f.write(f"owner_priv_key_b64: {owner.key.hex()}\n")

def generateUserAddress(path: str = "DemoUserKeys.txt"):
    a1 = w3.eth.account.create()
    a2 = w3.eth.account.create()
    print(f"account1: {a1.address}")
    print(f"account2: {a2.address}")
    with open(path, "w") as f:
        f.write("=== TrustMesh Demo Users ===\n")
        f.write(f"account1_address: {a1.address}\n")
        f.write(f"account1_priv_key_b64: {a1.key.hex()}\n")
        f.write("---------------------------\n")
        f.write(f"account2_address: {a2.address}\n")
        f.write(f"account2_priv_key_b64: {a2.key.hex()}\n")



def decode_log(contract, log):
    # Build event ABI map once
    abi_events = [e for e in contract.abi if e.get("type") == "event"]
    for abi in abi_events:
        try:
            a = get_event_data(contract.web3.codec, abi, log)
            print(f"Event Data : {a}")
            return a
        except Exception:
            continue
    return None

def generateEscrows(abi: list, contract_address: str, owner_priv_b64: str,
                    buyer_priv_b64: str, seller_priv_b64: str, usdcabi):

    # --- Default accounts (preserved from your code) ---
    agent = w3.eth.account.from_key("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
    buyer = w3.eth.account.from_key("0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a")
    seller = w3.eth.account.from_key("0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6")

    contract_address = Web3.to_checksum_address("0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")
    usdc_address = Web3.to_checksum_address("0x5FbDB2315678afecb367f032d93F642f64180aa3")

    expectedby = w3.eth.get_block("latest")["timestamp"] + 3 * 24 * 3600
    block = w3.eth.block_number
    amount = 400

    # --- Build contract instances ---
    contract = w3.eth.contract(address=contract_address, abi=abi)
    usdccontract = w3.eth.contract(address=usdc_address, abi=usdcabi)

    # --- Step 1: Approve transfer ---
    tx = usdccontract.functions.approve(contract.address, amount).build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 1_000_000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })
    signed = buyer.sign_transaction(tx)
    sent = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(sent)

    # Decode only USDC logs with USDC ABI
    for log in receipt["logs"]:
        if log["address"].lower() == usdc_address.lower():
            try:
                decoded = usdccontract.events.Transfer().process_log(log)
                print("USDC Transfer:", dict(decoded["args"]))
            except Exception:
                pass

    # --- Step 2: Create Escrow ---
    tx = contract.functions.createEscrow(seller.address, 200, expectedby).build_transaction({
        "from": buyer.address,
        "nonce": w3.eth.get_transaction_count(buyer.address),
        "gas": 1_000_000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })
    signed = buyer.sign_transaction(tx)
    sent = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(sent)

    # --- Step 3: Continuous polling (optional) ---
    while True:
        latest = w3.eth.block_number
        if latest >= block:
            logs = w3.eth.get_logs({
                "fromBlock": block,
                "toBlock": latest,
                "address": contract.address
            })
            for log in logs:
                try:
                    decoded = _decode_log(contract, log)
                    print(f"[{decoded['blockNumber']}] {decoded['event']} {dict(decoded['args'])}")
                except Exception:
                    pass
            block = latest + 1
        time.sleep(2)

def _decode_log(contract:Contract,log):
        for ev in [
        contract.events.EscrowCreated,
        contract.events.ShipmentLinked,
        contract.events.FundsReleased,
        contract.events.FundsRefunded,
        contract.events.EscrowExtended,
        contract.events.EscrowExpired,
        contract.events.EscrowCancelled,
    ]:
            try:
                return ev().process_log(log)
            except Exception:
                continue
        return None
def generate_env(path=".env", contract_address=None, abi_path=None):
    agent = w3.eth.account.create()
    env_lines = [
        f"AGENT_ADDRESS={agent.address}",
        f"AGENT_PRIV_KEY_Hex={agent.key.hex()}",
    ]
    if contract_address:
        env_lines.append(f"CONTRACT_ADDRESS={Web3.to_checksum_address(contract_address)}")
    if abi_path:
        with open(abi_path) as f:
            abi = f.read()
        env_lines.append(f"CONTRACT_ABI_JSON={json.dumps(json.loads(abi))}")
    with open(path, "w") as f:
        f.write("\n".join(env_lines))
    print(f".env written to {path}")
