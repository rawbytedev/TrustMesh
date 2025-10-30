// Author: rawbytedev
pragma solidity ^0.8.20;

/**
 * @title TrustMesh Escrow (Polished)
 * @notice AI-driven escrow for cross-border trade using USDC on Arc.
 * - Buyer deposits USDC
 * - Seller links a shipmentId
 * - AI agent (authorized role) releases/refunds/extends based on shipment events
 * - Time-locks and expiration provide safety rails
 */

interface IERC20 {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function transfer(address to, uint256 value) external returns (bool);
}

contract TrustMeshEscrow {
    // --- Roles ---
    address public owner;
    address public agent; // authorized AI backend

    // --- Basic reentrancy guard ---
    uint256 private _lock;
    modifier noReentrancy() {
        require(_lock == 0, "Reentrancy");
        _lock = 1;
        _;
        _lock = 0;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyAgent() {
        require(msg.sender == agent, "Only agent");
        _;
    }

    // --- Escrow state ---
    enum State { Pending, Linked, Released, Refunded, Extended, Expired, Cancelled }

    struct Escrow {
        address buyer;
        address seller;
        uint256 amount;
        string shipmentId;       // set by seller
        State state;
        uint256 createdAt;       // block timestamp
        uint256 linkedAt; // for hold period
        uint256 expectedBy;      // expected delivery deadline (epoch secs)
        uint256 extendedUntil;   // optional extension deadline
    }

    IERC20 public usdc;
    uint256 public escrowCount;
    mapping(uint256 => Escrow) public escrows;
    mapping(string => uint256) public shipmentToEscrow; // uniqueness
    // --- Config ---
    uint256 public defaultHoldDuration = 2 days;      // time-lock after link
    uint256 public maxExtensionDuration = 14 days;    // cap on extension length

    // --- Events (with rationale for explainability) ---
    event EscrowCreated(
        uint256 indexed escrowId,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        uint256 expectedBy
    );
    event ShipmentLinked(uint256 indexed escrowId, string shipmentId);
    event FundsReleased(uint256 indexed escrowId, address seller, string shipmentId, string reason);
    event FundsRefunded(uint256 indexed escrowId, address buyer, string shipmentId, string reason);
    event EscrowExtended(uint256 indexed escrowId, uint256 extendedUntil, string shipmentId, string reason);
    event EscrowExpired(uint256 indexed escrowId, string reason);
    event EscrowCancelled(uint256 indexed escrowId, string reason);
    event AgentUpdated(address indexed oldAgent, address indexed newAgent);
    event OwnerUpdated(address indexed oldOwner, address indexed newOwner);
    event ConfigUpdated(uint256 defaultHoldDuration, uint256 maxExtensionDuration);

    constructor(address _usdc, address _agent) {
        require(_usdc != address(0), "USDC required");
        owner = msg.sender;
        usdc = IERC20(_usdc);
        agent = _agent;
    }

    // --- Admin ---
    function setAgent(address _agent) external onlyOwner {
        require(_agent != address(0), "Invalid agent");
        emit AgentUpdated(agent, _agent);
        agent = _agent;
    }

    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid owner");
        emit OwnerUpdated(owner, _newOwner);
        owner = _newOwner;
    }

    function updateConfig(uint256 _defaultHoldDuration, uint256 _maxExtensionDuration) external onlyOwner {
        require(_maxExtensionDuration >= _defaultHoldDuration, "Config invalid");
        defaultHoldDuration = _defaultHoldDuration;
        maxExtensionDuration = _maxExtensionDuration;
        emit ConfigUpdated(defaultHoldDuration, maxExtensionDuration);
    }

    // --- Buyer creates escrow and deposits USDC ---
    function createEscrow(address _seller, uint256 _amount, uint256 _expectedBy) external noReentrancy returns (uint256) {
        require(_seller != address(0) && _seller != msg.sender, "Bad seller");
        require(_amount > 0, "Amount must be > 0");
        require(_expectedBy > block.timestamp, "Expected date must be future");

        escrowCount++;
        Escrow storage e = escrows[escrowCount];
        e.buyer = msg.sender;
        e.seller = _seller;
        e.amount = _amount;
        e.shipmentId = "";
        e.state = State.Pending;
        e.createdAt = block.timestamp;
        e.expectedBy = _expectedBy;
        e.extendedUntil = 0;

        // Pull USDC from buyer
        require(usdc.transferFrom(msg.sender, address(this), _amount), "USDC transfer failed");

        emit EscrowCreated(escrowCount, msg.sender, _seller, _amount, _expectedBy);
        return escrowCount;
    }

    // --- Seller links shipment to escrow ---
    function linkShipment(uint256 _escrowId, string calldata _shipmentId) external {
        Escrow storage e = escrows[_escrowId];
        require(msg.sender == e.seller, "Only seller");
        require(e.state == State.Pending, "Not pending");
        require(bytes(_shipmentId).length > 0, "Shipment required");
        require(shipmentToEscrow[_shipmentId] == 0, "Shipment already linked"); // uniqueness

        e.shipmentId = _shipmentId;
        e.state = State.Linked;
        e.linkedAt = block.timestamp;
        shipmentToEscrow[_shipmentId] = _escrowId;
        emit ShipmentLinked(_escrowId, _shipmentId);
    }

    // --- AI agent decisions ---
    function releaseFunds(uint256 _escrowId, string calldata _reason) external 	onlyAgent noReentrancy {
        Escrow storage e = escrows[_escrowId];
        require(e.state == State.Linked || e.state == State.Extended, "Not releasable");
        //  enforce a minimal hold period after link
        require(block.timestamp >= e.linkedAt + defaultHoldDuration, "Hold period");

        e.state = State.Released;
        require(usdc.transfer(e.seller, e.amount), "USDC transfer failed");
        emit FundsReleased(_escrowId, e.seller, e.shipmentId, _reason);
    }

    function refund(uint256 _escrowId, string calldata _reason) external onlyAgent noReentrancy {
        Escrow storage e = escrows[_escrowId];
        require(e.state == State.Linked || e.state == State.Extended, "Not refundable");

        e.state = State.Refunded;
        require(usdc.transfer(e.buyer, e.amount), "USDC transfer failed");
        emit FundsRefunded(_escrowId, e.buyer, e.shipmentId, _reason);
    }

    function extendEscrow(uint256 _escrowId, uint256 _extraSeconds, string calldata _reason) external onlyAgent {
        Escrow storage e = escrows[_escrowId];
        require(e.state == State.Linked || e.state == State.Extended, "Not extendable");
        require(_extraSeconds > 0 && _extraSeconds <= maxExtensionDuration, "Bad extension");

        uint256 base = e.extendedUntil == 0 ? e.expectedBy : e.extendedUntil;
        e.extendedUntil = base + _extraSeconds;
        e.state = State.Extended;

        emit EscrowExtended(_escrowId, e.extendedUntil, e.shipmentId, _reason);
    }

    // --- Safety rails: expiry & cancellation ---
    // Anyone can mark expired when deadline passed (transparent state), but only agent/buyer triggers outcomes.
    function markExpired(uint256 _escrowId, string calldata _reason) external {
        Escrow storage e = escrows[_escrowId];
        require(e.state == State.Linked || e.state == State.Extended, "Bad state");

        uint256 deadline = e.extendedUntil == 0 ? e.expectedBy : e.extendedUntil;
        require(block.timestamp > deadline, "Not expired");

        e.state = State.Expired;
        emit EscrowExpired(_escrowId, _reason);
    }

    // Buyer can cancel if never linked and past expectedBy (e.g seller never shipped)
    function cancelUnlinked(uint256 _escrowId, string calldata _reason) external noReentrancy {
        Escrow storage e = escrows[_escrowId];
        require(msg.sender == e.buyer, "Only buyer");
        require(e.state == State.Pending, "Not pending");

        require(block.timestamp > e.expectedBy, "Not past expected date");
        e.state = State.Cancelled;
        require(usdc.transfer(e.buyer, e.amount), "USDC transfer failed");
        emit EscrowCancelled(_escrowId, _reason);
    }

    // agent can finalize expired escrows to refund buyer
    function finalizeExpiredRefund(uint256 _escrowId, string calldata _reason) external onlyAgent noReentrancy {
        Escrow storage e = escrows[_escrowId];
        require(e.state == State.Expired, "Not expired");
        e.state = State.Refunded;
        require(usdc.transfer(e.buyer, e.amount), "USDC transfer failed");
        emit FundsRefunded(_escrowId, e.buyer, e.shipmentId, _reason);
    }
}
