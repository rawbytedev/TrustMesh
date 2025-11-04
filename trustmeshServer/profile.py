import logging
import json, time
from web3 import Web3
from core import Storage, ArcHandler

def load_config():
    with open("config.json") as f:
        return json.load(f)

def startw3(cfg):
    w3 = Web3(Web3.HTTPProvider(cfg["provider_url"]))
    with open(cfg["abi_path"]) as f:
        abi = json.load(f)
    return abi, w3
def main():
    cfg = load_config()
    abi, w3 =startw3(cfg)
    storage = Storage()
    arc = ArcHandler(cfg["provider_url"], cfg["contract_address"], abi, cfg["agent_key"], storage)

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

def CreateEscrow(arc, buyer, w3, address, amount:int=None):
    escrowamount = amount if amount else int(input("escrow amount-> ")) 
    expected_by = int(time.time())+360 # 3600= 1 hours
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
    
def normalflow(arc, buyer, seller, w3):
    escrows = []
    for i in range(3):
        res = CreateEscrow(arc, buyer, w3, seller.address, 100)
        escrows.append(res)
    for i in range(3):
        LinkEscrow(arc, seller, w3, res[i], ship=f"ship-n-{i}")
    
def loaddemo(arc, cfg, w3):
    created = []
    linked = []
    cancelled = []
    print("=== Starting Demo ===")
    buyer = cfg["buyer_key"]
    seller = cfg["seller_key"]
    logging.info(f"Loaded configurations with values buyer: {buyer.address}, seller: {seller.address}")
    logging.info(f"blockchain RPC : {cfg["provider_url"]}")
    print("=== Demo menu ===")
    print("1- Normal Escrows") # Created -> Linked -> Released
    print("2- Bad Escrows") # Created -> badlink
    print("3- CanceledUnlinked") # Created ->(no link)canceled
    print("4- Extended") # Created -> Linked -> Extended
    print("5- Expired") # (Created /-> Linked /-> Extended )-> Expired
    print("6- Released") # Created ->(Linked / -> Extended )-> Released
    print("7- Refunded") # Created -> (canceled /->Expired /-> BadEscrow)       
    choice = input("Choose")
    if choice == "1":

            
    
    print("===== Demo menu ====")

if __name__ == "__main__":
    main()