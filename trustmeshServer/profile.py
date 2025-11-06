import logging
import json, time
from web3 import Web3
from core import Storage, ArcHandler

USDC_DECIMALS = 6

def load_config():
    with open("config.json") as f:
        return json.load(f)

def startw3(cfg):
    w3 = Web3(Web3.HTTPProvider(cfg["CHAIN_URL"]))
    with open(cfg["ABI_PATH"]) as f:
        abi = json.load(f)
    return abi, w3
def main():
    cfg = load_config()
    abi, w3 =startw3(cfg)
    storage = Storage()
    arc = ArcHandler(cfg["CHAIN_URL"], cfg["CONTRACT_ADDRESS"], abi, cfg["AGENT_KEY"], storage)

    while True:
        role = input("Select role: [1] Buyer [2] Seller [3] Demo [q] Quit: ")
        if role == "1":
            buyer_menu(arc, cfg, w3)
        elif role == "2":
            seller_menu(arc, cfg, w3)
        elif role =="3":
            loaddemo(arc, cfg, w3)
        elif role == "q":
            break

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

def _send_tx(fn,key, w3,*args):
    """Helper to sign and send a transaction"""
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

def CreateEscrow(arc, buyer, w3, address, amount:int=None, expectedby:int=None):
    escrowamount = amount if amount else int(input("escrow amount-> ")) 
    expected_by = expectedby if expectedby else int(time.time())+360 # 3600= 1 hours
    receipt = _send_tx(arc.contract.functions.createEscrow, buyer, w3, address, escrowamount,expected_by)
    logs = arc.contract.events.EscrowCreated().process_receipt(receipt)
    for ev in logs:
        print("Escrow created:", ev["args"]["escrowId"])
        return ev["args"]["escrowId"]
    
def LinkEscrow(arc, seller, w3, id:int=None, ship:str=None):
    escrowId = id if id else int(input("escrowID: "))
    shipId = ship if ship else input("Id of shipment")
    receipt = _send_tx(arc.contract.functions.linkShipment,seller, w3 ,escrowId, shipId)
    logs = arc.contract.events.EscrowCreated().process_receipt(receipt)
    for ev in logs:
        print("Shipment linked:", ev["args"]["escrowId"], ev["args"]["shipmentId"])
        return ev["args"]["escrowId"]

def cancelUnlinked(arc, buyer, w3, id:int= None, reason:str="Demo"):
    escrow_id = id if id else int(input("escrow_id: "))
    reason =reason if reason else input("reason: ")
    receipt = _send_tx(arc.contract.functions.cancelUnlinked, buyer, w3, escrow_id, reason)
    logs = arc.contract.events.EscrowCreated().process_receipt(receipt)
    for ev in logs:
        print("Escrow Cancelled:", ev["args"]["escrowId"])
        return ev["args"]["escrowId"]

def markExpired(arc, buyer, w3, id:int=None, reason:str="Demo"):
    escrow_id = id if id else int(input("escrow_id: "))
    reason =reason if reason else input("reason: ")
    receipt = _send_tx(arc.contract.functions.markExpired, buyer, w3, escrow_id, reason)
    logs = arc.contract.events.EscrowCreated().process_receipt(receipt)
    for ev in logs:
        print("Escrow Expired:", ev["args"]["escrowId"])
        return ev["args"]["escrowId"]

def normalflow(arc, buyer, seller, w3, count:int=3):
    block = w3.eth.block_number
    escrows = []
    lk = []
    for i in range(count):
        res = CreateEscrow(arc, f"0x{buyer.key.hex()}", w3, seller.address, 100)## wait for call to succeed
        escrows.append(res)
    for i in range(count):
        tmp = LinkEscrow(arc, f"0x{seller.key.hex()}", w3, escrows[i], ship=f"ship-n-{escrows[i]}")
        lk.append(tmp)
    if len(escrows) == count and len(lk) == count:
        print("Creation and Linking of Escrow successful")
    sel = input("wait for release?(Y,n): ")
    if sel.lower() == "n":
        pass
    else:
        captureEvents(arc, w3, block)

def Expiredflow(arc, buyer, seller, w3, count:int=3):
    block = w3.eth.block_number
    escrows = []
    exp = []
    for i in range(count-1):
        res = CreateEscrow(arc, f"0x{buyer.key.hex()}", w3, seller.address, 100, expectedby=40)## wait for call to succeed
        escrows.append(res)
    res = CreateEscrow(arc, f"0x{buyer.key.hex()}", w3, seller.address, 100, expectedby=120)## extended
    escrows.append(res)
    for i in range(count):
        LinkEscrow(arc, f"0x{seller.key.hex()}", w3, escrows[i], ship=f"ship-cl-{i}")
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
        captureEvents(arc, w3, block)

def Cancelledflow(arc, buyer, seller, w3, count:int=3):
    block = w3.eth.block_number
    escrows = []
    cancelled = []
    for i in range(count):
        res = CreateEscrow(arc, buyer, w3, seller.address, 100, expectedby=30)## wait for call to succeed
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
        captureEvents(arc, w3, block)

def to_micro_usdc(amount):
    return int(amount* (10 ** USDC_DECIMALS))

def captureEvents(arc, w3, block):
    while True:
        latest = w3.eth.block_number
        if latest >= block:
            logs = w3.eth.get_logs({
                "fromBlock": block,
                "toBlock": latest,
                "address": arc.contract.address
            })
            for log in logs:
                try:
                    decoded = _decode_log(contract, log)
                    print(f"[{decoded['blockNumber']}] {decoded['event']} {dict(decoded['args'])}")
                except Exception:
                    pass
            block = latest + 1
        time.sleep(2)

def _decode_log(contract,log):
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
    print("=== Starting Demo ===")
    buyer = w3.eth.account.from_key(cfg["buyer_key"])
    seller = w3.eth.account.from_key(cfg["seller_key"])
    logging.info(f"Loaded configurations with values buyer: {buyer.address}, seller: {seller.address}")
    logging.info(f"blockchain RPC : {cfg["CHAIN_URL"]}")
    print("=== Demo menu ===")
    print("1- Normal Escrows(Released)") # Created -> (Linked / -> Extended ) -> Released
    print("2- CanceledUnlinked") # Created ->(no link)canceled -> (Refunded)
    print("3- Expired") # (Created /-> Linked /-> Extended )-> Expired -> (Refunded)       
    choice = input("Choose")
    if choice == "1":
        normalflow(arc, buyer, seller, w3)
    elif choice == "2":
        Cancelledflow(arc, buyer, seller, w3)
    elif choice == "3":
        Expiredflow(arc, buyer, seller, w3)
    else:
        pass
    
    
if __name__ == "__main__":
    main()