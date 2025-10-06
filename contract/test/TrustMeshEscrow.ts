import { expect } from "chai";
import { network } from "hardhat";


const { ethers } = await network.connect();

describe("TrustMeshEscrow", function () {
  let owner, agent, buyer, seller;
  let usdc, escrow;
  beforeEach(async () => {
    // setup
    [owner, agent, buyer, seller] = await ethers.getSigners();
    // Deploy MockUSDC
    const MockUSDC = await ethers.getContractFactory("MockUSDC");
    usdc = await MockUSDC.connect(owner).deploy();
    await usdc.waitForDeployment();
    const Escrow = await ethers.getContractFactory("TrustMeshEscrow");
    escrow = await Escrow.connect(owner).deploy(usdc.getAddress(), agent.getAddress());
    await escrow.waitForDeployment();
  })
  it("should create escrow and release funds", async () => {
    
    // Mint to buyer
    const amount = ethers.parseUnits("50000", 6);
    await usdc.connect(owner).mint(buyer, amount)
    await ethers.provider.send("evm_mine");
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 3 * 24 * 3600;
    // approve usdc spend
    await usdc.connect(buyer).approve(escrow.getAddress(), amount);
    const tx = await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
    const escrowId = 1;
    await escrow.connect(seller).linkShipment(escrowId, "SHIP-123");

    // Fast-forward time to satisfy hold period
    await ethers.provider.send("evm_increaseTime", [3 * 24 * 3600]);
    await ethers.provider.send("evm_mine", []);

    // Agent releases funds
    await escrow.connect(agent).releaseFunds(escrowId, "Delivered at port");

    const receiverBalance = await usdc.balanceOf(seller.address);
    expect(receiverBalance).to.equal(amount);
  });
  it("should fail if balance is insufficient", async () => {
    // Mint to buyer
    const amount = ethers.parseUnits("50000", 6);
    await usdc.connect(owner).mint(buyer, amount)
    await ethers.provider.send("evm_mine");
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 3 * 24 * 3600;
    const highAmount = ethers.parseUnits("999999", 18);
    await expect(
      escrow.connect(buyer).createEscrow(seller.getAddress(), highAmount, expectedBy)
    ).to.be.revertedWith("balance");
  });
  it("should create, link, and release escrow", async function () {    
    // Mint to buyer
    const amount = ethers.parseUnits("50000", 6);
    await usdc.connect(owner).mint(buyer, amount)
    const balance = await usdc.balanceOf(buyer.address)
    // Buyer create escrow on contract
    // Create escrow
    await ethers.provider.send("evm_mine");
    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 3 * 24 * 3600;
    // approve usdc spend
    await usdc.connect(buyer).approve(escrow.getAddress(), amount);
    const tx = await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
    const receipt = await tx.wait();
    const escrowId = 1;


    // Seller links shipment
    await escrow.connect(seller).linkShipment(escrowId, "SHIP-123");

    // Fast-forward time to satisfy hold period
    await ethers.provider.send("evm_increaseTime", [3 * 24 * 3600]);
    await ethers.provider.send("evm_mine", []);

    // Agent releases funds
    await escrow.connect(agent).releaseFunds(escrowId, "Delivered at port");

    // Seller should now have funds
    const sellerBalance = await usdc.balanceOf(seller.address);
    expect(sellerBalance).to.equal(amount);
  });

  it("should refund buyer if anomaly", async function () {
    

    const amount = ethers.parseUnits("100", 6);
    await usdc.connect(owner).mint(buyer.address, amount);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 3 * 24 * 3600;
    await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);

    await escrow.connect(seller).linkShipment(1, "SHIP-999");

    // Agent refunds buyer
    await escrow.connect(agent).refund(1, "Tampering anomaly");

    const buyerBalance = await usdc.balanceOf(buyer.address);
    expect(buyerBalance).to.equal(amount);
  });
  it("should fail if event no returned", async function () {

    const amount = ethers.parseUnits("100", 6);
    await usdc.connect(owner).mint(buyer.address, amount);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 3 * 24 * 3600;
    await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
    await escrow.connect(seller).linkShipment(1, "SHIP-999");
    /*
    const escrow2 = await ethers.getContractAt("TrustMeshEscrow", await escrow.getAddress());
    await escrow2.on("EscrowCreated", (escrowId, buyer, seller, amount, expectedBy) => {
     console.log("EscrowCreated:", { escrowId, buyer, seller, amount: amount.toString(), expectedBy });*/
   //});
  })
});
