from utils import *

if __name__ == "__main__":
    print("===== TrustMesh Dev Tools =====")
    print("1 - Generate Config Addresses (agent, owner)")
    print("2 - Generate User Addresses (buyer, seller)")
    print("3 - Generate Demo escrows (emit and decode events)")
    
    select = int(input("~> "))

    if select == 1:
        path = input("path to store: ")
        generateConfigAddress(path)
    elif select == 2:
        path = input("path to store: ")
        generateUserAddress(path)
    elif select == 3:
        abi_path = input("path to contract ABI (json): ")
        usdc_abi = input("path to abi: ")
        contract_address = input("contract address: ").strip()
        owner_priv_b64 = input("owner priv key (base64): ").strip()
        buyer_priv_b64 = input("buyer priv key (base64): ").strip()
        seller_priv_b64 = input("seller priv key (base64): ").strip()

        import json
        abi_path = "trustmesh.json"
        usdc_abi = "usdc.json"
        with open(abi_path) as f:
            abi = json.load(f)
        with open(usdc_abi) as f:
            usdcabi = json.load(f)
        generateEscrows(abi, contract_address, owner_priv_b64, buyer_priv_b64, seller_priv_b64, usdcabi)
