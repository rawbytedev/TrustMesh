# TrustMesh

**TrustMesh** is an AI-powered agent that automates **cross-border trade payments** using **Arc blockchain + USDC**

##  System Architecture

```graph
Smart Contract (Arc, Solidity)
        ⬍
     ArcHandler (Python)
        ⬍
┌───────────────┬───────────────┐
│ Feedback API  │ Dashboard UI  │
│ (FastAPI)     │(FastAPI/React)│
└───────────────┴───────────────┘
        ⬍
       AI Agent (LangChain)
```

## Problem

- **Cross‑border B2B trade** is plagued by **payment risk, delays, and disputes**.  
- SMEs in emerging markets often can’t trust counterparties: buyers fear prepaying, sellers fear shipping without funds.  
- Current solutions (letters of credit, escrow services) are **slow, expensive, and opaque**

## 1. Core Concept

**AI agent as a trusted intermediary for cross‑border trade.**  

- Buyer pays in USDC → funds held in Arc escrow.  
- AI agent monitors trade signals (mock shipping/IoT/customs data).  
- Agent decides: release, hold, or refund.  
- Optional: cross‑chain settlement via CCTP if seller prefers another chain.  
- Every action explained in plain language for transparency.

### Solution

- **TrustMesh** is an AI agent that autonomously manages **end‑to‑end cross‑border trade payments** on Arc with USDC.  
- **How it works:**  
  1. **Smart escrow contract** on Arc holds USDC from buyer.  
  2. **AI agent monitors trade signals**: shipping data, IoT container logs, customs clearance, and even news feeds (For hackathon demo we use a custom MockServer which feeds shipments news to Ai).  
  3. **Conditional release**:  
     - If goods are confirmed delivered → auto‑release to seller.  
     - If anomalies (delays, tampering, fraud cues) → agent extends escrow, requests verification, or triggers partial refund.  
  4. **Cross‑chain settlement**: If seller prefers another chain, agent uses **CCTP** to deliver USDC seamlessly.  
  5. **Explainability**: Every action is logged in plain language for both parties (“Funds held due to customs delay in NYC ; expected release in 48h”).  

### Workflow

- Buyer deposits USDC into escrow.  
- Seller links shipment ID.  
- AI agent monitors shipment events (delivery, delay, anomaly).  
- Based on signals, the agent releases, refunds, or extends escrow.  
- All decisions are explainable and enforced on-chain.


- Show 3 flows:  
  1. Normal delivery → release funds.  
  2. Delay → extend escrow.  
  3. Fraud/anomaly → refund buyer.  
- dashboard to visualize escrow state and AI decisions.

## Features

- **Explainability**: Every action has a reason string, logged on-chain.  
- **Security**: Seller must link shipment ID from their wallet, preventing hijacking.  
- **Fallback logic**: Optional pickup code or expiry safeguards add resilience.  
- **Composable**: Can integrate with real logistics APIs post-hackathon.