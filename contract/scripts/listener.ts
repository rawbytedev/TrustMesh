import { expect } from "chai";
import { Console } from "console";
import { Addressable } from "ethers";
import { network } from "hardhat";
import { serialize } from "v8";

const deployedAddress = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
const { ethers } = await network.connect();

async function main() {
  const escrows = await ethers.getContractAt("TrustMeshEscrow", deployedAddress);
  
  escrows.on("EscrowCreated", (escrowId, buyer, seller, amount, expectedBy) => {
     console.log("EscrowCreated:", { escrowId, buyer, seller, amount: amount.toString(), expectedBy });
   });
   escrows.on("ShipmentLinked", (escrowId, shipmentId) => {
     console.log("ShipmentLinked:", { escrowId, shipmentId });
   });
   
}
// Boilerplate to run the script and catch errors
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});