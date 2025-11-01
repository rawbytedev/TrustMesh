import { expect } from "chai";
import { Console } from "console";
import { Addressable } from "ethers";
import { network } from "hardhat";
import { serialize } from "v8";

const { ethers } = await network.connect();

async function listener(deployedAddress: string | Addressable) {
  const escrows = await ethers.getContractAt("TrustMeshEscrow", deployedAddress);
  escrows.on("EscrowCreated", (escrowId, buyer, seller, amount, expectedBy) => {
     console.log("EscrowCreated:", { escrowId, buyer, seller, amount: amount.toString(), expectedBy });
   });
}
async function main() {
  const restart = true
  
  const [deployer, agent, buyer, seller] = await ethers.getSigners();

  console.log("Deploying contracts with account:", deployer.address);
  console.log("deployer: ", deployer)
  // 1. Deploy MockUSDC
  const MockUSDC = await ethers.getContractFactory("MockUSDC");
  const usdc = await MockUSDC.connect(deployer).deploy();
  await usdc.waitForDeployment();
  console.log("MockUSDC deployed to:", await usdc.getAddress());
  
  // 2. Deploy TrustMeshEscrow with USDC + agent address
  const Escrow = await ethers.getContractFactory("TrustMeshEscrow");
  const escrow = await Escrow.connect(deployer).deploy(usdc.getAddress(), agent.address);
  await escrow.waitForDeployment();
  console.log("TrustMeshEscrow deployed to:", await escrow.getAddress());
  // 3. Mint some USDC to buyer for testing
  const mintAmount = ethers.parseUnits("100000", 6);
  await usdc.connect(deployer).mint(buyer.address, mintAmount);
  console.log(`Minted ${mintAmount.toString()} USDC to buyer:`, buyer.address);
  const txamount = ethers.parseUnits("100", 6)
  const now = (await ethers.provider.getBlock("latest")).timestamp;
  const expectedBy = now + 3 * 24 * 3600;
  await usdc.connect(buyer).approve(escrow.getAddress(), mintAmount)
  await escrow.connect(buyer).createEscrow(seller.address, txamount, expectedBy)
  console.log("Buyers new balance: ",await usdc.balanceOf(buyer))
  const id = 1
  await escrow.connect(seller).linkShipment(id, "Ship-56")
  // Fast-forward time to satisfy hold period
  await ethers.provider.send("evm_increaseTime", [2 * 24 * 3600]);
  await escrow.connect(agent).releaseFunds(id, "delivered")
  console.log("Sellers new balance: ", await usdc.balanceOf(seller))
}

// Boilerplate to run the script and catch errors
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
