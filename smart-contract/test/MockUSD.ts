import { network } from "hardhat";
import { expect } from "chai";

const { ethers } = await network.connect()

describe("MockUSDC Tests", function () {
  let deployer, alice, bob;
  let usdc;
  const decimals = 6;
  const amount = ethers.parseUnits("1000", decimals);

  beforeEach(async () => {
    [deployer, alice, bob] = await ethers.getSigners();
    const MockUsd = await ethers.getContractFactory("MockUSDC");
    usdc = await MockUsd.connect(deployer).deploy();
    await usdc.waitForDeployment();
  });

  it("should mint tokens to an address", async () => {
    await usdc.connect(deployer).mint(alice.address, amount);
    const balance = await usdc.balanceOf(alice.address);
    expect(balance).to.equal(amount);
  });

  it("should approve allowance for another address", async () => {
    await usdc.connect(deployer).mint(alice.address, amount);
    await usdc.connect(alice).approve(bob.address, amount);
    const allowance = await usdc.allowance(alice.address, bob.address);
    expect(allowance).to.equal(amount);
  });

  it("should transferFrom with sufficient allowance", async () => {
    await usdc.connect(deployer).mint(alice.address, amount);
    await usdc.connect(alice).approve(bob.address, amount);

    await usdc.connect(bob).transferFrom(alice.address, bob.address, amount);
    const bobBalance = await usdc.balanceOf(bob.address);
    expect(bobBalance).to.equal(amount);
  });

  it("should fail transferFrom if allowance is too low", async () => {
    await usdc.connect(deployer).mint(alice.address, amount);
    await usdc.connect(alice).approve(bob.address, ethers.parseUnits("500", decimals));

    await expect(
      usdc.connect(bob).transferFrom(alice.address, bob.address, amount)
    ).to.be.revertedWith("allowance");
  });

  it("should fail transferFrom if balance is too low", async () => {
    await usdc.connect(deployer).mint(alice.address, ethers.parseUnits("500", decimals));
    await usdc.connect(alice).approve(bob.address, amount);

    await expect(
      usdc.connect(bob).transferFrom(alice.address, bob.address, amount)
    ).to.be.revertedWith("balance");
  });
});
