import json
import time
from web3 import Web3
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
        f.write(f"agent_priv_key_hex: 0x{agent.key.hex()}\n")
        f.write(f"owner_address: {owner.address}\n")
        f.write(f"owner_priv_key_hex: 0x{owner.key.hex()}\n")

def generateUserAddress(path: str = "DemoUserKeys.txt"):
    a1 = w3.eth.account.create()
    a2 = w3.eth.account.create()
    print(f"account1: {a1.address}")
    print(f"account2: {a2.address}")
    with open(path, "w") as f:
        f.write("=== TrustMesh Demo Users ===\n")
        f.write(f"account1_address: {a1.address}\n")
        f.write(f"account1_priv_key_hex: 0x{a1.key.hex()}\n")
        f.write("---------------------------\n")
        f.write(f"account2_address: {a2.address}\n")
        f.write(f"account2_priv_key_hex: 0x{a2.key.hex()}\n")


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

if __name__ == "__main__":
    print("===== TrustMesh Dev Tools =====")
    print("1 - Generate Config Addresses (agent, owner)")
    print("2 - Generate User Addresses (buyer, seller)")

    select = int(input("~> "))

    if select == 1:
        path = input("path to store: ")
        generateConfigAddress(path)
    elif select == 2:
        path = input("path to store: ")
        generateUserAddress(path)