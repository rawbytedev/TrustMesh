import { error } from "console";
import { network } from "hardhat";

const { ethers } = await network.connect();
async function main(){
    const [deployer] = await ethers.getSigners();
    console.log("Deploying with account:", deployer.address);
    const contract = await ethers.getContractFactory("TrustMeshEscrow");
    const cont = await contract.deploy("0x3600000000000000000000000000000000000000", "0xa29A11f0018c71E136932FCC6533c6c29CCf404d");
    await cont.waitForDeployment()
    console.log("trustMesh deployed to:", await cont.getAddress());
}

main().catch((error) => { 
    console.error(error);
    process.exitCode=1;
})