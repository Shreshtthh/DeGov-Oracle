# DeGov Oracle API Documentation

## Overview

The DeGov Oracle API provides programmatic access to decentralized governance functionality through both agent interaction and direct canister communication. This documentation covers the complete API surface for developers building integrations or custom interfaces.

## Architecture

### Agent API Layer
The Fetch.ai uAgent exposes HTTP endpoints for natural language interaction and structured API calls.

### Canister API Layer  
Direct Internet Computer canister interface using Candid IDL for type-safe blockchain interaction.

### Communication Protocol
CBOR-encoded messages over HTTP Gateway Protocol for authentic ICP integration.

## Agent Endpoints

### Base Configuration
```
Base URL: https://your-agent.onrender.com
Content-Type: application/json
Protocol: HTTP/1.1
```

### Message Processing Endpoint

#### POST /submit
Process natural language governance commands.

**Request Format**:
```json
{
  "message": "string",
  "sender": "string (optional)",
  "context": "object (optional)"
}
```

**Response Format**:
```json
{
  "success": true,
  "response": "string",
  "intent": "string",
  "parameters": "object",
  "timestamp": "ISO8601"
}
```

**Example Request**:
```bash
curl -X POST https://your-agent.onrender.com/submit \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create proposal: Fund marketing with options For, Against",
    "sender": "user123"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "response": "Proposal #42 created successfully!\n\nTitle: Fund marketing\nVoting is now open for 72 hours.",
  "intent": "CREATE_PROPOSAL",
  "parameters": {
    "title": "Fund marketing",
    "description": "Fund marketing",
    "options": ["For", "Against"],
    "duration_hours": 72
  },
  "timestamp": "2024-03-15T10:30:00Z"
}
```

### Health Check Endpoint

#### GET /health
Verify agent status and canister connectivity.

**Response Format**:
```json
{
  "status": "healthy",
  "agent_address": "string",
  "canister_url": "string",
  "uptime": "number",
  "last_canister_ping": "ISO8601"
}
```

## Canister Interface

### Type Definitions

#### Proposal
```candid
type Proposal = record {
  id: nat;
  title: text;
  description: text;
  options: vec text;
  votes: vec record { text; nat };
  voters: vec text;
  created: int;
  deadline: int;
  status: ProposalStatus;
  creator: text;
};
```

#### ProposalStatus
```candid
type ProposalStatus = variant {
  Active;
  Closed;
};
```

#### CreateProposalRequest
```candid
type CreateProposalRequest = record {
  title: text;
  description: text;
  options: vec text;
  duration_hours: nat;
};
```

#### VoteRequest
```candid
type VoteRequest = record {
  proposal_id: nat;
  option: text;
  voter_id: text;
};
```

### Public Methods

#### createProposal
Create a new governance proposal.

**Signature**:
```candid
createProposal: (CreateProposalRequest, text) -> (Result_1);
```

**Parameters**:
- `request`: Proposal creation parameters
- `creator`: Creator identity string

**Returns**:
- `Ok(nat)`: Proposal ID on success
- `Err(text)`: Error message on failure

**Example Call** (Python):
```python
from ic.client import Client
from ic.identity import Identity
from ic.agent import Agent

# Initialize client
identity = Identity()
client = Client(url="https://icp0.io")
agent = Agent(identity, client)

# Create proposal
result = await agent.update_raw(
    canister_id="your-canister-id",
    method_name="createProposal",
    encode_args=candid.encode([{
        "title": "Fund Marketing Campaign",
        "description": "Allocate budget for Q2 marketing",
        "options": ["Approve", "Reject"],
        "duration_hours": 72
    }, "creator-id"])
)
```

#### castVote
Submit a vote on an active proposal.

**Signature**:
```candid
castVote: (VoteRequest) -> (Result);
```

**Parameters**:
- `request`: Vote submission parameters

**Returns**:
- `Ok(text)`: Success confirmation
- `Err(text)`: Error message

**Validation Rules**:
- Proposal must exist and be active
- Voter cannot have previously voted
- Option must be valid for the proposal
- Current time must be before deadline

#### getProposal (Query)
Retrieve detailed information about a specific proposal.

**Signature**:
```candid
getProposal: (nat) -> (Result_2) query;
```

**Parameters**:
- `proposal_id`: Numeric proposal identifier

**Returns**:
- `Ok(Proposal)`: Complete proposal data
- `Err(text)`: Error if proposal not found

#### getActiveProposals (Query)  
List all proposals currently accepting votes.

**Signature**:
```candid
getActiveProposals: () -> (vec Proposal) query;
```

**Returns**:
- Array of active proposal objects

#### getProposalResults (Query)
Get current vote tallies for a proposal.

**Signature**:
```candid
getProposalResults: (nat) -> (Result_3) query;
```

**Parameters**:
- `proposal_id`: Numeric proposal identifier

**Returns**:
- `Ok(vec record { text; nat })`: Vote counts by option
- `Err(text)`: Error if proposal not found

#### closeProposal
Manually close an active proposal (admin function).

**Signature**:
```candid
closeProposal: (nat) -> (Result);
```

**Parameters**:
- `proposal_id`: Proposal to close

**Returns**:
- `Ok(text)`: Success confirmation
- `Err(text)`: Error message

## Error Handling

### Agent Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `INTENT_PARSE_ERROR` | Failed to understand command | Use supported command patterns |
| `PARAMETER_MISSING` | Required information missing | Include all required parameters |
| `CANISTER_UNREACHABLE` | Cannot connect to blockchain | Check network connectivity |
| `VALIDATION_FAILED` | Input validation failed | Verify parameter formats |

### Canister Error Messages

| Error | Cause | Solution |
|-------|-------|---------|
| `"Proposal not found"` | Invalid proposal ID | Verify proposal exists |
| `"Proposal is no longer active"` | Attempting to vote on closed proposal | Check proposal status |
| `"Voting deadline has passed"` | Proposal expired | View results instead of voting |
| `"You have already voted"` | Duplicate vote attempt | One vote per user limit |
| `"Invalid voting option"` | Option not in proposal | Use exact option text |

## Rate Limiting

### Agent Endpoints
- 100 requests per minute per IP
- 1000 requests per hour per user
- Burst allowance: 10 requests per second

### Canister Limits
- Query calls: No practical limit
- Update calls: Limited by ICP cycles balance
- Large proposals: Consider pagination for 100+ options

## Authentication

### Agent Level
- Optional sender identification
- No authentication required for basic usage
- API key support for production integrations

### Canister Level
- Anonymous principal for query calls
- Identity-based authentication for update calls
- Signature verification for vote attribution

## Integration Examples

### Web Interface Integration

```javascript
// Frontend integration example
class DeGovClient {
  constructor(agentUrl) {
    this.baseUrl = agentUrl;
  }
  
  async sendCommand(message, userId) {
    const response = await fetch(`${this.baseUrl}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, sender: userId })
    });
    
    return response.json();
  }
  
  async createProposal(title, options) {
    const message = `Create proposal: ${title} with options ${options.join(', ')}`;
    return this.sendCommand(message, this.getCurrentUser());
  }
  
  async vote(proposalId, option) {
    const message = `Vote ${option} on proposal ${proposalId}`;
    return this.sendCommand(message, this.getCurrentUser());
  }
}

// Usage
const client = new DeGovClient('https://your-agent.onrender.com');
await client.createProposal('Fund Development', ['Yes', 'No']);
await client.vote(1, 'Yes');
```

### Discord Bot Integration

```python
import discord
import aiohttp

class DeGovBot(discord.Client):
    def __init__(self, agent_url):
        super().__init__()
        self.agent_url = agent_url
    
    async def on_message(self, message):
        if message.content.startswith('!gov '):
            command = message.content[5:]  # Remove "!gov "
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.agent_url}/submit",
                    json={
                        "message": command,
                        "sender": str(message.author.id)
                    }
                ) as response:
                    result = await response.json()
                    await message.channel.send(result['response'])

# Usage
bot = DeGovBot('https://your-agent.onrender.com')
bot.run('your-discord-token')
```

### Direct Canister Integration

```python
# Direct canister communication
import asyncio
from ic.client import Client
from ic.identity import Identity
from ic.candid import encode, decode

class DirectCanisterClient:
    def __init__(self, canister_id):
        self.canister_id = canister_id
        self.client = Client(url="https://icp0.io")
        self.identity = Identity()  # Use your identity
        
    async def create_proposal(self, title, description, options):
        args = encode([{
            "title": title,
            "description": description,
            "options": options,
            "duration_hours": 72
        }, "creator-id"])
        
        result = await self.client.update_raw(
            canister_id=self.canister_id,
            method_name="createProposal",
            arg=args,
            sender=self.identity.sender()
        )
        
        return decode(result)
    
    async def get_active_proposals(self):
        result = await self.client.query_raw(
            canister_id=self.canister_id,
            method_name="getActiveProposals",
            arg=encode([])
        )
        
        return decode(result)

# Usage
client = DirectCanisterClient("your-canister-id")
proposals = await client.get_active_proposals()
```

## Development Tools

### Testing Utilities

```python
# Test client for integration testing
class DeGovTestClient:
    def __init__(self, agent_url):
        self.agent_url = agent_url
        
    async def run_test_suite(self):
        tests = [
            ("Create proposal test", self.test_create_proposal),
            ("Vote casting test", self.test_vote_casting),
            ("Status check test", self.test_status_check),
            ("Active proposals test", self.test_active_proposals)
        ]
        
        for test_name, test_func in tests:
            try:
                await test_func()
                print(f"✅ {test_name} passed")
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
```

### Monitoring and Observability

```python
# Health monitoring
async def monitor_agent_health(agent_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{agent_url}/health") as response:
            health_data = await response.json()
            
            if health_data['status'] != 'healthy':
                # Alert logic here
                send_alert(f"Agent unhealthy: {health_data}")
```

## Performance Optimization

### Query Optimization
- Use query calls for read-only operations
- Batch multiple queries when possible
- Cache results appropriately for user interfaces

### Update Call Efficiency  
- Minimize update calls due to cycle costs
- Batch vote submissions where applicable
- Implement proper retry logic for failed updates

### Network Optimization
- Use connection pooling for multiple requests
- Implement request compression for large payloads
- Cache static data like proposal options

## Security Considerations

### Input Validation
- All user inputs validated before blockchain submission
- SQL injection and XSS prevention in custom interfaces
- Rate limiting to prevent abuse

### Identity Management
- Secure storage of user identities and keys
- Proper signature verification for vote attribution
- Anonymous voting option consideration

### Data Privacy
- Proposal content is public on blockchain
- Voter identities may be pseudonymous or anonymous
- Consider privacy implications for sensitive governance topics