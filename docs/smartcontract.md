# TrustMesh Smart Contract

## Events

The design ensure that TrustMesh listen to all events and only takes into account what is needed the rest are stored directly into key:value database.
For production pruning the database of olds events helps with storage management, since everything is available onchain rebuilding database from scratch is possible.
Each event signals a change in state of an Escrow

```ts
ShipmentLinked(uint256 indexed escrowId, string shipmentId); // when linked
FundsReleased(uint256 indexed escrowId, address seller, string reason); // when funds a released
FundsRefunded(uint256 indexed escrowId, address buyer, string reason); // when refund occurs
EscrowExtended(uint256 indexed escrowId, uint256 extendedUntil, string reason); // if escrow is extended
EscrowExpired(uint256 indexed escrowId, string reason); // escrow is expired
EscrowCancelled(uint256 indexed escrowId, string reason); // escrow canceled by users
AgentUpdated(address indexed oldAgent, address indexed newAgent); // agent authorized address is changed
OwnerUpdated(address indexed oldOwner, address indexed newOwner); // when owner transfer occurs
ConfigUpdated(uint256 defaultHoldDuration, uint256 maxExtensionDuration); // when config changes occurs
```

each created escrow has the same lifecycle which can defer depending on users involvements and shipments feedback

normal events flow: approve → create escrow → LinkShipment → release funds
events flows with delay: approve → create escrow → LinkShipment → extended escrow → release funds
`
User (Circle Wallet UI) → Smart Contract (Escrow)
                               ↓ emits events
                        ArcHandler (server listener)
                               ↓ stores locally
                           AI Agent (via LangChain)
                               ↓ calls ArcHandler methods
                        Smart Contract (actions back)
`