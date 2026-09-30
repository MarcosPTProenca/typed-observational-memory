# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

This is a trustless Battleship game implementation using ZK-SNARKs for anti-cheat mechanisms. The system consists of:

- **Zero-Knowledge Circuits** (`circuits/`): Circom circuits for board validation and hit/miss verification
- **Smart Contracts** (`contracts/`): Solidity contracts for game logic and proof verification  
- **Frontend App** (`app/`): React/Vite application for gameplay interface
- **Data Layer** (`infra/`): Amp data engineering with PostgreSQL and monitoring

## Package Management

This project uses **pnpm** as the package manager. Always use `pnpm` commands instead of `npm`.

## Development Commands

### Install and Setup
- `just install` - Install dependencies
- `just up [services]` - Start service dependencies (Postgres, Amp, or specific services)
- `just deploy` - Deploy the Battleship smart contract to local network

### Development Servers  
- `just dev` - Run all development services in parallel (app, proxy, amp)

### Testing and Quality
- `just test [args]` - Run both Solidity and TypeScript tests
- `just test-sol [args]` - Test Solidity contracts only
- `just test-ts [args]` - Run TypeScript tests only
- `just check` - Run linting and type checking for both Solidity and TypeScript
- `just fmt [args]` - Format both Solidity and TypeScript code
- `just fmt-sol [args]` - Format Solidity code only
- `just fmt-ts [args]` - Format TypeScript code only
- `just lint-sol [args]` - Lint Solidity code only
- `just lint-ts [args]` - Lint TypeScript code only

### Infrastructure
- `just logs [services]` - View logs for specific services or all services
- `just stop [services]` - Stop specific services or all services
- `just down` - Stop all services and remove volumes

### Circuits
- `just circuits` - Re-compile circuit(s) without setup/ceremony using random entropy

## Architecture

### Circuit Layer
- `circuits/board.circom` - Validates ship placement and generates board commitments
- `circuits/impact.circom` - Verifies hit/miss claims and maintains state transitions
- `circuits/ship.circom` + `circuits/utils.circom` - Helper circuits for validation

### Smart Contract Layer  
- `contracts/src/Battleship.sol` - Main game logic and lifecycle management
- `contracts/src/BoardVerifier.sol` - Generated Groth16 verifier for board proofs
- `contracts/src/ImpactVerifier.sol` - Generated Groth16 verifier for impact proofs

### Frontend Application
- `app/src/routes/` - TanStack Router pages for game interface
- `app/src/components/` - React components for game board, player actions
- `app/src/lib/` - Blockchain interaction, queries, and game logic utilities

### Data Infrastructure
- `infra/amp/` - Data indexing and query layer for blockchain events
- `infra/postgres/` - Database for indexed game data
- `infra/grafana/` - Monitoring dashboards and metrics

## Key Technical Details

### ZK-SNARK Workflow
1. **Board Setup**: Players generate proofs of valid ship placement using `board.circom`
2. **Game Turns**: Each hit/miss claim requires proof from `impact.circom` 
3. **State Chain**: Commitments link game states to prevent cheating
4. **Verification**: Smart contract validates all proofs before state transitions

### Anti-Cheat Mechanisms
- Ship positions committed cryptographically and cannot be changed
- Hit/miss results proven with zero-knowledge, preventing false claims  
- State commitments prevent manipulation of hit counts between turns
- Duplicate shots prevented by on-chain bit-packed grids

### Development Stack
- **Frontend**: React + Vite + TanStack Router + Tailwind CSS
- **Blockchain**: Foundry + Viem + Wagmi for Ethereum interaction
- **Circuits**: Circom + SnarkJS + Groth16 proving system
- **Data**: Amp + PostgreSQL for event indexing and queries
- **Testing**: Vitest for TypeScript, Foundry for Solidity

## Testing Strategy

The test suite covers multiple attack vectors and edge cases:
- `contracts/test/` contains comprehensive Solidity tests including fuzz testing
- `app/test/` contains circuit testing and proof generation validation
- Tests verify anti-cheat mechanisms and game rule enforcement

## Configuration Files

- `foundry.toml` - Foundry configuration with circuit verifier exclusions
- `vite.config.ts` - Vite dev server with proxy setup for RPC and Amp
- `amp.config.ts` - Data indexing configuration for blockchain events
- `docker-compose.yaml` - Service orchestration for development environment