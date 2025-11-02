import { network } from "hardhat";

const { ethers } = await network.connect();

async function Main() {
    const [deployer, agent, buyer, seller] = await ethers.getSigners();
    const usdc = await ethers.getContractAt("MockUSDC", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    ;(await usdc).waitForDeployment()
    const escrow = ethers.getContractAt("TrustMeshEscrow", "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")
    ;(await escrow).waitForDeployment()
    console.log("current buyer balance", await usdc.balanceOf(buyer.address))
    const txamount = ethers.parseUnits("100", 6)
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 3 * 24 * 3600;
    await usdc.connect(buyer).approve((await escrow).getAddress(), txamount)
    await (await escrow).connect(buyer).createEscrow(seller.address, txamount, expectedBy)
    const id = 4
  await (await escrow).connect(seller).linkShipment(id, "Ship")
  // Fast-forward time to satisfy hold period
  await ethers.provider.send("evm_increaseTime", [2 * 24 * 3600]);
  await (await escrow).connect(agent).releaseFunds(id, "delivered")
  console.log("Sellers new balance: ", await usdc.balanceOf(seller))
}

Main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});