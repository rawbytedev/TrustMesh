import { network } from "hardhat";

const { ethers } = await network.connect();

async function Main() {
const [deployer, agent, buyer] = await ethers.getSigners();
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
}

Main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});