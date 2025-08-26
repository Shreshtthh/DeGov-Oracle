# DeGov Oracle Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying DeGov Oracle in both development and production environments. The system consists of two main components: a Python-based Fetch.ai uAgent and a Motoko smart contract on the Internet Computer.

## Prerequisites

### Required Software

**Local Development**:
- Python 3.10 or higher
- dfx (DFINITY Canister SDK) 0.15.0+
- Git 2.30+
- Node.js 16+ (for some dfx operations)

**Production Deployment**:
- GitHub account (for code repository)
- Render account (for agent hosting)
- Internet Computer wallet with cycles

### System Requirements

**Development Machine**:
- 4GB RAM minimum, 8GB recommended
- 10GB free disk space
- Stable internet connection

**Production Environment**:
- Render: Automatic scaling, no specific requirements
- Internet Computer: Cycles for canister deployment and operation

## Local Development Setup

### 1. Repository Setup

```bash
# Clone the repository
git clone https://github.com/your-org/degov-oracle
cd degov-oracle

# Verify directory structure
ls -la
# Should show: agent/, canister/, docs/, scripts/, README.md
```

### 2. Internet Computer Local Network

```bash
# Install dfx (if not already installed)
sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"

# Verify installation
dfx --version

# Start local IC replica
dfx start --background --clean

# Verify replica is running
dfx ping local
```

### 3. Canister Deployment (Local)

```bash
# Navigate to canister directory
cd canister

# Install Motoko dependencies (if using vessel)
vessel install

# Deploy to local network
dfx deploy --network local

# Get local canister information
dfx canister id degov_oracle --network local
dfx canister call degov_oracle getActiveProposals
```

**Expected Output**:
```bash
Creating a wallet canister on the local network.
Deploying: degov_oracle
...
URLs:
  degov_oracle: http://127.0.0.1:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai
```

### 4. Agent Setup (Local)

```bash
# Navigate to agent directory
cd ../agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
```

**Edit `.env` file**:
```env
# Agent Configuration
AGENT_NAME=degov_oracle
AGENT_SEED=local-development-seed-12345
PORT=8001

# Canister Configuration (update with your local canister ID)
LOCAL_CANISTER_URL=http://127.0.0.1:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai
CANISTER_URL=http://127.0.0.1:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai

# Development settings
DEBUG=true
ENVIRONMENT=development
```

### 5. Start Local Agent

```bash
# Ensure virtual environment is active
source venv/bin/activate

# Start the agent
python src/main.py
```

**Expected Output**:
```
DeGov Oracle Agent starting...
Agent address: agent1q2w3e4r5t6y7u8i9o0p1a2s3d4f5g6h7j8k9l0
Agent wallet: fetch1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0
Running on port: 8001
Canister URL: http://127.0.0.1:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai
[INFO]: DeGov Oracle Agent started!
```

### 6. Local Testing

```bash
# In a new terminal, run integration tests
cd scripts
python test_integration.py

# Test with curl
curl -X POST http://localhost:8001/submit \
  -H "Content-Type: application/json" \
  -d '{"message": "show active proposals", "sender": "test-user"}'
```

## Production Deployment

### Phase 1: Canister Deployment to IC Mainnet

#### 1. Cycles Acquisition

**Option A: DFINITY Cycles Faucet** (Recommended for development):
```bash
# Create mainnet identity
dfx identity new mainnet-deploy
dfx identity use mainnet-deploy

# Get your principal ID
dfx identity get-principal

# Visit https://faucet.dfinity.org/
# Submit your principal ID to receive free cycles
```

**Option B: Purchase ICP and Convert**:
```bash
# Buy ICP from exchange (Coinbase, Binance, etc.)
# Send ICP to your dfx identity address
dfx ledger account-id

# Top up cycles wallet
dfx cycles top-up AMOUNT --network ic
```

#### 2. Mainnet Canister Deployment

```bash
# Navigate to canister directory
cd canister

# Deploy to Internet Computer mainnet
dfx deploy --network ic

# Verify deployment
dfx canister id degov_oracle --network ic
dfx canister status degov_oracle --network ic
```

**Expected Output**:
```bash
Deploying: degov_oracle
...
URLs:
  degov_oracle: https://a4gq6-oaaaa-aaaab-qaa4q-cai.raw.icp0.io/?id=your-canister-id

Canister Status:
Status: Running
Memory allocation: 0
Compute allocation: 0
Freezing threshold: 2_592_000
Memory Size: Nat(2471838)
Balance: 3_000_000_000_000 Cycles
Module hash: 0x4d...1f2e
```

#### 3. Test Mainnet Canister

```bash
# Test basic functionality
dfx canister call degov_oracle getActiveProposals --network ic

# Test proposal creation
dfx canister call degov_oracle createProposal '(
  record {
    title = "Test Proposal";
    description = "Testing mainnet deployment";
    options = vec {"Yes"; "No"};
    duration_hours = 72;
  },
  "deployment-test"
)' --network ic
```

### Phase 2: Agent Deployment to Render

#### 1. Prepare Repository

```bash
# Ensure your code is in a Git repository
git add .
git commit -m "Production deployment ready"
git push origin main

# Create render.yaml in project root (if not exists)
```

**Create `render.yaml`**:
```yaml
services:
  - type: web
    name: degov-oracle-agent
    env: python
    plan: free  # or starter for production
    buildCommand: cd agent && pip install -r requirements.txt
    startCommand: cd agent && python src/main.py
    healthCheckPath: /health
    envVars:
      - key: AGENT_NAME
        value: degov_oracle
      - key: AGENT_SEED
        generateValue: true  # Render generates secure random value
      - key: PYTHON_VERSION
        value: 3.11.0
```

#### 2. Deploy on Render

1. **Login to Render**:
   - Visit [render.com](https://render.com)
   - Sign up/login with your GitHub account

2. **Create New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `degov-oracle` repository

3. **Configure Service**:
   - **Name**: `degov-oracle-agent`
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `cd agent && pip install -r requirements.txt`
   - **Start Command**: `cd agent && python src/main.py`

4. **Set Environment Variables**:
   - `AGENT_NAME`: `degov_oracle`
   - `AGENT_SEED`: Generate secure random string
   - `CANISTER_URL`: Your mainnet canister URL from Phase 1
   - `PORT`: Leave empty (Render sets automatically)

5. **Deploy**:
   - Click "Create Web Service"
   - Monitor build logs for any errors
   - Note your service URL: `https://degov-oracle-agent.onrender.com`

#### 3. Verify Agent Deployment

```bash
# Test agent health
curl https://your-agent.onrender.com/health

# Test basic functionality
curl -X POST https://your-agent.onrender.com/submit \
  -H "Content-Type: application/json" \
  -d '{"message": "help", "sender": "test"}'
```

### Phase 3: Agentverse Registration

#### 1. Gather Required Information

```bash
# Get agent address from Render logs or run locally:
python agent/src/main.py
# Look for: "Agent address: agent1..."

# Your information:
# - Agent Name: DeGov Oracle
# - Agent Address: [from logs]
# - Agent Endpoint: https://your-agent.onrender.com
```

#### 2. Register on Agentverse

1. **Visit Agentverse**:
   - Go to [agentverse.ai](https://agentverse.ai)
   - Create account and login

2. **Register Agent**:
   - Click "Register New Agent"
   - Fill out registration form:
     - **Name**: `DeGov Oracle`
     - **Agent Address**: `agent1q2w3e4r5t6y7u8i9o0p1a2s3d4f5g6h7j8k9l0` (from logs)
     - **Agent Endpoint**: `https://degov-oracle-agent.onrender.com`
     - **Description**: `Universal governance-as-a-service agent for decentralized communities. Create proposals, cast votes, and manage DAO governance through natural language.`
     - **Tags**: `governance`, `dao`, `voting`, `icp`, `blockchain`

3. **Verify Registration**:
   - Test agent discovery in ASI:One
   - Verify endpoint connectivity
   - Confirm agent responds to test messages

## Environment Configuration

### Development Environment Variables

**`.env` for Local Development**:
```env
# Agent Configuration
AGENT_NAME=degov_oracle
AGENT_SEED=local-development-seed-change-this
PORT=8001

# Canister URLs
LOCAL_CANISTER_URL=http://127.0.0.1:4943/?canisterId=your-local-canister-id
CANISTER_URL=http://127.0.0.1:4943/?canisterId=your-local-canister-id

# Development Settings
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Production Environment Variables

**Render Environment Variables**:
```env
# Agent Configuration (Required)
AGENT_NAME=degov_oracle
AGENT_SEED=production-secure-seed-generated-by-render

# Canister Configuration (Required)
CANISTER_URL=https://your-canister-id.icp0.io

# Runtime Configuration (Optional)
PYTHON_VERSION=3.11.0
ENVIRONMENT=production
LOG_LEVEL=WARNING

# Render automatically sets:
# PORT=10000 (or assigned port)
```

## Monitoring and Maintenance

### Health Monitoring

**Agent Health Endpoint**:
```bash
# Check agent status
curl https://your-agent.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "agent_address": "agent1...",
  "canister_url": "https://...",
  "uptime": 86400,
  "last_canister_ping": "2024-03-15T10:30:00Z"
}
```

**Canister Status Monitoring**:
```bash
# Check canister status
dfx canister status degov_oracle --network ic

# Monitor cycles balance
dfx canister call degov_oracle getActiveProposals --network ic
```

### Log Analysis

**Render Logs Access**:
1. Go to Render dashboard
2. Select your service
3. Click "Logs" tab
4. Monitor for errors or unusual activity

**Key Log Messages to Monitor**:
- `Agent started successfully` - Normal startup
- `Canister connection failed` - Network/connectivity issues  
- `Intent classification error` - User input processing problems
- `Rate limit exceeded` - Usage spike detection

### Performance Optimization

**Agent Performance Tuning**:
```python
# In production, consider these optimizations:

# Connection pooling
AIOHTTP_CONNECTOR_LIMIT = 100
AIOHTTP_CONNECTOR_LIMIT_PER_HOST = 30

# Request timeouts
CANISTER_REQUEST_TIMEOUT = 30
AGENT_RESPONSE_TIMEOUT = 10

# Caching
PROPOSAL_CACHE_TTL = 60  # Cache active proposals for 1 minute
```

**Canister Optimization**:
- Monitor cycles consumption
- Implement proposal archiving for old data
- Consider pagination for large datasets

## Troubleshooting

### Common Deployment Issues

#### Canister Deployment Failures

**Issue**: `dfx deploy --network ic` fails with "Insufficient cycles"
```bash
# Solution: Top up cycles
dfx wallet balance --network ic
dfx cycles top-up 1000000000000 --network ic  # 1T cycles
```

**Issue**: "Canister not found" error
```bash
# Solution: Verify canister exists and network is correct
dfx canister id degov_oracle --network ic
dfx ping ic
```

#### Agent Deployment Issues

**Issue**: Render build fails with dependency errors
```yaml
# Solution: Update requirements.txt and Python version
buildCommand: cd agent && pip install --upgrade pip && pip install -r requirements.txt
envVars:
  - key: PYTHON_VERSION
    value: 3.11.0
```

**Issue**: Agent starts but can't reach canister
```bash
# Solution: Verify CANISTER_URL is correct
curl -X POST https://your-agent.onrender.com/submit \
  -H "Content-Type: application/json" \
  -d '{"message": "help"}'

# Check Render logs for connection errors
```

#### Agentverse Registration Problems

**Issue**: Agent not discoverable in ASI:One
- Verify agent endpoint is publicly accessible
- Check agent address matches registration
- Ensure agent responds to health checks

**Issue**: Agent responds but with errors
- Check Render logs for runtime errors
- Verify environment variables are set correctly
- Test canister connectivity manually

### Performance Issues

#### Slow Response Times

**Diagnosis**:
```bash
# Test agent response time
time curl -X POST https://your-agent.onrender.com/submit \
  -H "Content-Type: application/json" \
  -d '{"message": "show active proposals"}'

# Test canister response time  
time dfx canister call degov_oracle getActiveProposals --network ic
```

**Solutions**:
- Implement response caching for frequent queries
- Optimize canister queries with pagination
- Consider upgrading Render plan for better performance

#### High Cycles Consumption

**Diagnosis**:
```bash
# Monitor cycles usage over time
dfx canister status degov_oracle --network ic | grep Balance
```

**Solutions**:
- Implement proposal archiving
- Optimize update calls frequency
- Use query calls where possible instead of update calls

### Security Considerations

#### Agent Security

**Best Practices**:
- Use secure, random AGENT_SEED values
- Implement rate limiting for API endpoints
- Validate all user inputs before processing
- Monitor for abuse patterns in logs

**Render Security**:
```yaml
# In render.yaml, enable security features:
services:
  - type: web
    healthCheckPath: /health
    autoDeploy: false  # Manual deployments for production
    envVars:
      - key: AGENT_SEED
        generateValue: true  # Auto-generate secure values
```

#### Canister Security

**Access Control**:
```motoko
// Implement admin controls for sensitive operations
private func isAuthorized(caller: Principal) : Bool {
    // Add your authorization logic
    true
};

public func closeProposal(proposalId: Nat) : async Result.Result<Text, Text> {
    if (not isAuthorized(msg.caller)) {
        return #err("Unauthorized");
    };
    // ... rest of function
};
```

## Scaling Considerations

### Horizontal Scaling

**Agent Scaling**:
- Render automatically scales based on traffic
- Consider multiple agent instances for high availability
- Implement load balancing if using custom infrastructure

**Canister Scaling**:
- Internet Computer automatically handles scaling
- Monitor cycles consumption during high usage
- Consider data partitioning for very large datasets

### Data Management

**Proposal Lifecycle**:
```motoko
// Implement automatic proposal archiving
public func archiveExpiredProposals() : async Nat {
    let now = Time.now();
    var archivedCount = 0;
    
    for ((id, proposal) in proposals.entries()) {
        if (proposal.deadline < now and proposal.status == #Active) {
            let archivedProposal = {
                proposal with status = #Closed
            };
            proposals.put(id, archivedProposal);
            archivedCount += 1;
        };
    };
    
    archivedCount
};
```

## Backup and Recovery

### Code Repository Backup

```bash
# Ensure code is backed up in version control
git remote -v
git push origin main
git tag -a v1.0.0 -m "Production release"
git push origin v1.0.0
```

### Canister State Backup

```bash
# Export canister state (for backup/migration)
dfx canister call degov_oracle getActiveProposals --network ic > proposals_backup.txt

# Consider implementing export functions in your canister:
# dfx canister call degov_oracle exportAllProposals --network ic
```

### Disaster Recovery Plan

1. **Agent Recovery**:
   - Redeploy from GitHub repository
   - Restore environment variables from secure storage
   - Verify agent connectivity and functionality

2. **Canister Recovery**:
   - Canister data is permanently stored on IC
   - Re-deploy canister code if needed: `dfx deploy --network ic`
   - Verify data integrity after redeployment

## Maintenance Schedule

### Regular Maintenance Tasks

**Weekly**:
- Check Render service status and logs
- Monitor canister cycles balance
- Review usage patterns and performance metrics

**Monthly**:
- Update dependencies if security patches available
- Archive old proposals if storage optimization needed
- Review and update documentation

**Quarterly**:
- Performance optimization review
- Security audit of access patterns
- Backup verification and disaster recovery testing

### Upgrade Procedures

**Agent Updates**:
```bash
# Development workflow
git checkout -b feature/new-update
# Make changes
git commit -m "Add new feature"
git push origin feature/new-update
# Create pull request, review, merge
# Render automatically deploys from main branch
```

**Canister Updates**:
```bash
# Test locally first
dfx deploy --network local
# Test functionality
# Deploy to mainnet
dfx deploy --network ic
# Verify upgrade successful
dfx canister status degov_oracle --network ic
```

This deployment guide provides a complete pathway from local development to production deployment with monitoring and maintenance procedures.