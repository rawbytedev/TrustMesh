import { expect } from "chai";
import { network } from "hardhat";


const { ethers } = await network.connect();

describe("TrustMeshEscrow Normal Test", function () {
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

describe("TrustMeshEscrow Stress Tests", function () {
  let owner, agent, buyer, seller;
  let usdc, escrow;

  beforeEach(async () => {
    [owner, agent, buyer, seller] = await ethers.getSigners();
    const MockUSDC = await ethers.getContractFactory("MockUSDC");
    usdc = await MockUSDC.connect(owner).deploy();
    await usdc.waitForDeployment();

    const Escrow = await ethers.getContractFactory("TrustMeshEscrow");
    escrow = await Escrow.connect(owner).deploy(usdc.getAddress(), agent.getAddress());
    await escrow.waitForDeployment();
  });

  it("should handle creating 50 escrows in a row", async () => {
    const amount = ethers.parseUnits("1000", 6);
    await usdc.connect(owner).mint(buyer.address, amount * 50n);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount * 50n);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 7 * 24 * 3600;

    for (let i = 0; i < 50; i++) {
      await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
    }

    const count = await escrow.escrowCount();
    expect(count).to.equal(50n);
  });

  it("should link and release multiple escrows", async () => {
    const amount = ethers.parseUnits("100", 6);
    await usdc.connect(owner).mint(buyer.address, amount * 10n);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount * 10n);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 7 * 24 * 3600;

    // Create 10 escrows
    for (let i = 0; i < 10; i++) {
      await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
      await escrow.connect(seller).linkShipment(i + 1, `SHIP-${i}`);
    }

    // Fast-forward beyond hold period
    await ethers.provider.send("evm_increaseTime", [3 * 24 * 3600]);
    await ethers.provider.send("evm_mine", []);

    // Release all escrows
    for (let i = 0; i < 10; i++) {
      await escrow.connect(agent).releaseFunds(i + 1, "Stress release");
    }

    const sellerBalance = await usdc.balanceOf(seller.address);
    expect(sellerBalance).to.equal(amount * 10n);
  });

  it("should revert if shipmentId reused", async () => {
    const amount = ethers.parseUnits("100", 6);
    await usdc.connect(owner).mint(buyer.address, amount * 2n);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount * 2n);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 7 * 24 * 3600;

    await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
    await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);

    await escrow.connect(seller).linkShipment(1, "SHIP-XYZ");
    await expect(
      escrow.connect(seller).linkShipment(2, "SHIP-XYZ")
    ).to.be.revertedWith("Shipment already linked");
  });

  it("should revert if extension exceeds maxExtensionDuration", async () => {
    const amount = ethers.parseUnits("100", 6);
    await usdc.connect(owner).mint(buyer.address, amount);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 7 * 24 * 3600;

    await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);
    await escrow.connect(seller).linkShipment(1, "SHIP-EXT");

    const tooLong = (await escrow.maxExtensionDuration()) + 1n;
    await expect(
      escrow.connect(agent).extendEscrow(1, tooLong, "Too long")
    ).to.be.revertedWith("Bad extension");
  });

  it("should allow buyer to cancel unlinked escrow after expiry", async () => {
    const amount = ethers.parseUnits("100", 6);
    await usdc.connect(owner).mint(buyer.address, amount);
    await usdc.connect(buyer).approve(escrow.getAddress(), amount);

    const now = (await ethers.provider.getBlock("latest")).timestamp;
    const expectedBy = now + 1 * 24 * 3600;

    await escrow.connect(buyer).createEscrow(seller.address, amount, expectedBy);

    // Fast-forward beyond expectedBy
    await ethers.provider.send("evm_increaseTime", [2 * 24 * 3600]);
    await ethers.provider.send("evm_mine", []);

    await escrow.connect(buyer).cancelUnlinked(1, "Seller never shipped");

    const buyerBalance = await usdc.balanceOf(buyer.address);
    expect(buyerBalance).to.equal(amount);
  });
});