import asyncio
import logging
import json, time
from typing import List, Optional
from web3 import Web3

USDC_DECIMALS = 6
logging.basicConfig(level=logging.INFO)
logs = logging.getLogger(__name__)

class ArcHandler:
    """Handle all interaction with Arc Blockchain
    Stripped down for demo purposes
    """
    def __init__(self, provider_url:str=None, contract_address=None, abi:List[str]=None, agent_key:str=None):
        self.w3 = Web3(Web3.HTTPProvider(provider_url)) if provider_url else None
        self.contract = self.w3.eth.contract(address=contract_address, abi=abi) if contract_address else None
        self.agent = self.w3.eth.account.from_key(agent_key) if agent_key else None
    
        
def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)

def start_web3(cfg):
    w3 = Web3(Web3.HTTPProvider(cfg["CHAIN_URL"]))
    with open(cfg["ABI_PATH"]) as f:
        abi = json.load(f)
    return abi, w3


def buyer_menu(arc, cfg, w3):
    while True:
        print("\nBuyer Menu")
        print("[1] Create Escrow")
        print("[2] CancelUnlinked")
        print("[b] Back")
        choice = input("> ")
        if choice == "1":
            seller = input("Seller address: ")
            if seller == "":
                seller = w3.eth.account.from_key(cfg["seller_key"]).address
            CreateEscrow(arc, cfg["buyer_key"], w3, seller)
        if choice == "2":
            seller = input("Seller address(empty for default): ")
            if seller == "":
                seller = w3.eth.account.from_key(cfg["seller_key"]).address
            cancelUnlinked(arc, cfg["buyer_key"], w3)
        elif choice == "b":
            return

def seller_menu(arc, cfg, w3):
    while True:
        print("\nSeller Menu")
        print("[1] Link Shipment")
        print("[b] Back")
        choice = input("> ")
        if choice == "1":
            LinkEscrow(arc, cfg["seller_key"], w3)
        elif choice == "b":
            return


def normalflow(arc, buyer, seller, w3, count:int=3):
    block = w3.eth.block_number
    escrows = []
    lk = []
    for i in range(count):
        res = CreateEscrow(arc, f"0x{buyer.key.hex()}", w3, seller.address, 100, 20)## wait for call to succeed
        escrows.append(res)
    for i in range(count):
        tmp = LinkEscrow(arc, f"0x{seller.key.hex()}", w3, escrows[i], shipment_id=f"ship-n-{escrows[i]}")
        lk.append(tmp)
    if len(escrows) == count and len(lk) == count:
        print("Creation and Linking of Escrow successful")
    sel = input("wait for release?(Y,n): ")
    if sel.lower() == "n":
        pass
    else:
        capture_events(arc, w3, block)

def Expiredflow(arc, buyer, seller, w3, count:int=3):
    block = w3.eth.block_number
    escrows = []
    exp = []
    for i in range(count-1):
        res = CreateEscrow(arc, f"0x{buyer.key.hex()}", w3, seller.address, 100, expected_by=40)## wait for call to succeed
        escrows.append(res)
    res = CreateEscrow(arc, f"0x{buyer.key.hex()}", w3, seller.address, 100, expected_by=120)## extended
    escrows.append(res)
    for i in range(count):
        LinkEscrow(arc, f"0x{seller.key.hex()}", w3, escrows[i], shipment_id=f"ship-xr-{i}")
    ## time limit 60s
    print("waiting for escrow to expire")
    time.sleep(60)
    for i in range(count-1):
        tmp = markExpired(arc, f"0x{buyer.key.hex()}", w3, escrows[i])
        exp.append(tmp)
    time.sleep(60)
    tmp = markExpired(arc, f"0x{buyer.key.hex()}", w3, escrows[-1])
    exp.append(tmp)
    if len(exp) == len(escrows):
        print("MarkedExpired Successfully")
    sel = input("wait for refund?(Y,n): ")
    if sel.lower() == "n":
        pass
    else:
        capture_events(arc, w3, block)

def Cancelledflow(arc, buyer, seller, w3, count:int=3):
    block = w3.eth.block_number
    escrows = []
    cancelled = []
    for i in range(count):
        res = CreateEscrow(arc, buyer, w3, seller.address, 100, expected_by=30)## wait for call to succeed
        escrows.append(res)
    print("Waiting for expected date to past")
    time.sleep(30)
    for i in range(count):
        res = cancelUnlinked(arc, buyer, w3, escrows[i])
        cancelled.append(res)
    if len(escrows) == len(cancelled):
        print("CancelledUnlinked successfull")
    sel = input("wait for refund?(Y,n): ")
    if sel.lower() == "n":
        pass
    else:
        capture_events(arc, w3, block)


def _send_tx(fn, key, w3, *args):
    """Helper to sign and send a transaction with error handling"""
    try:
        account = w3.eth.account.from_key(key)
        tx = fn(*args).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 500000,
            "gasPrice": w3.to_wei("5", "gwei"),
        })
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return dict(receipt)
    except Exception as e:
        logs.error(f"Transaction failed: {e}", exc_info=True)
        return None

def CreateEscrow(arc, buyer_key, w3, seller_addr, amount:int=None, expected_by:int=None):
    escrow_amount = amount or int(input("Escrow amount -> "))
    expected_by = (int(time.time())+expected_by) if expected_by else int(time.time()) + 30
    receipt = _send_tx(arc.contract.functions.createEscrow, buyer_key, w3, seller_addr, escrow_amount, expected_by)
    if not receipt:
        return None
    for log in receipt["logs"]:
        decoded = _decode_log(arc.contract, log)
        if decoded and decoded["event"] == "EscrowCreated":
            escrow_id = decoded["args"]["escrowId"]
            logs.info(f"Escrow created: {escrow_id}")
            return escrow_id

def LinkEscrow(arc, seller_key, w3, escrow_id=None, shipment_id=None):
    escrow_id = escrow_id or int(input("Escrow ID: "))
    shipment_id = shipment_id or input("Shipment ID: ")
    receipt = _send_tx(arc.contract.functions.linkShipment, seller_key, w3, escrow_id, shipment_id)
    if not receipt:
        return None
    for log in receipt["logs"]:
        decoded = _decode_log(arc.contract, log)
        if decoded and decoded["event"] == "ShipmentLinked":
            escrow_id = decoded["args"]["escrowId"]
            shipment_id = decoded["args"]["shipmentId"]
            logs.info(f"Shipment linked: {escrow_id} -> {shipment_id}")
            return escrow_id

def cancelUnlinked(arc, buyer_key, w3, escrow_id=None, reason="Demo"):
    escrow_id = escrow_id or int(input("Escrow ID: "))
    reason = reason or input("Reason: ")
    receipt = _send_tx(arc.contract.functions.cancelUnlinked, buyer_key, w3, escrow_id, reason)
    if not receipt:
        return None
    for log in receipt["logs"]:
        decoded = _decode_log(arc.contract, log)
        if decoded and decoded["event"] == "EscrowCancelled":
            escrow_id = decoded["args"]["escrowId"]
            logs.info(f"Escrow cancelled: {escrow_id}")
            return escrow_id

def markExpired(arc, buyer_key, w3, escrow_id=None, reason="Demo"):
    escrow_id = escrow_id or int(input("Escrow ID: "))
    reason = reason or input("Reason: ")
    receipt = _send_tx(arc.contract.functions.markExpired, buyer_key, w3, escrow_id, reason)
    if not receipt:
        return None
    for log in receipt["logs"]:
        decoded = _decode_log(arc.contract, log)
        if decoded and decoded["event"] == "EscrowExpired":
            escrow_id = decoded["args"]["escrowId"]
            logs.info(f"Escrow expired: {escrow_id}")
            return escrow_id
def to_micro_usdc(amount: float) -> int:
    return int(amount * (10 ** USDC_DECIMALS))

def capture_events(arc, w3, start_block):
    """Continuously capture and decode escrow events"""
    while True:
        latest = w3.eth.block_number
        if latest >= start_block:
            clogs = w3.eth.get_logs({
                "fromBlock": start_block,
                "toBlock": latest,
                "address": arc.contract.address
            })
            for log in clogs:
                decoded = _decode_log(arc.contract, log)
                if decoded:
                    logs.info(f"[{decoded['blockNumber']}] {decoded['event']} {dict(decoded['args'])}")
            start_block = latest + 1
        time.sleep(2)

def _decode_log(contract, log):
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

def loaddemo(arc, cfg, w3):
    buyer = w3.eth.account.from_key(cfg["buyer_key"])
    seller = w3.eth.account.from_key(cfg["seller_key"])
    logs.info(f"Demo loaded with buyer={buyer.address}, seller={seller.address}, RPC={cfg['CHAIN_URL']}")

    menu = {
        "1": lambda: normalflow(arc, buyer, seller, w3),
        "2": lambda: Cancelledflow(arc, buyer, seller, w3),
        "3": lambda: Expiredflow(arc, buyer, seller, w3),
    }

    print("=== Demo Menu ===")
    print("1- Normal Escrows (Released)")
    print("2- Cancelled Unlinked")
    print("3- Expired Escrows")
    choice = input("Choose: ")
    if choice in menu:
        menu[choice]()

def main():
    cfg = load_config()
    abi, w3 = start_web3(cfg)
    arc = ArcHandler(cfg["CHAIN_URL"], cfg["CONTRACT_ADDRESS"], abi, cfg["AGENT_KEY"])

    while True:
        role = input("Select role: [1] Buyer [2] Seller [3] Demo [q] Quit: ")
        if role == "1":
            buyer_menu(arc, cfg, w3)
        elif role == "2":
            seller_menu(arc, cfg, w3)
        elif role == "3":
            loaddemo(arc, cfg, w3)
        elif role.lower() == "q":
            break

if __name__ == "__main__":
    main()
