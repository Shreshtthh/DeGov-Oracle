# DeGov Oracle User Guide

## Overview

DeGov Oracle is an intelligent governance agent that enables communities to create, manage, and participate in decentralized voting processes through natural language interaction. Built on Fetch.ai's agent framework and secured by Internet Computer blockchain storage, it provides a seamless bridge between human communication and on-chain governance.

## Core Capabilities

### Proposal Management
Create governance proposals with custom voting options that are permanently stored on the blockchain. Each proposal includes a title, description, voting options, and configurable duration.

### Vote Casting
Participate in active proposals by selecting from available options. The system ensures one-vote-per-user and prevents duplicate voting through unique voter identification.

### Real-Time Status Monitoring
Access current vote tallies, participation rates, and proposal status with instant blockchain queries.

### Active Proposal Discovery
Browse all open proposals to understand current governance activities and available voting opportunities.

## Command Reference

### Proposal Creation

**Purpose**: Create new governance proposals for community voting

**Required Elements**:
- Proposal title or description
- Voting options (minimum 2)
- Duration (defaults to 72 hours if not specified)

**Supported Patterns**:
```
"Create proposal: [TITLE] with options [OPTION1], [OPTION2]"
"New proposal [DESCRIPTION], options [OPTION1] and [OPTION2]"
"Propose [TOPIC] with voting choices [OPTION1], [OPTION2], [OPTION3]"
```

**Examples**:
```
"Create proposal: Allocate $10k for marketing campaign with options Approve, Reject"
"New proposal to hire a community manager with options Yes, No, Postpone"
"Propose updating the governance structure, options For, Against, Abstain"
```

**Response Format**:
- Confirmation message with assigned proposal ID
- Proposal title echo
- Voting duration information
- Current status confirmation

### Vote Casting

**Purpose**: Submit votes on active proposals

**Required Elements**:
- Proposal ID (numeric identifier)
- Voting option (must match available choices)
- Valid voter identification

**Supported Patterns**:
```
"Vote [OPTION] on proposal [ID]"
"I vote [OPTION] on proposal [ID]"
"Cast vote [OPTION] for proposal [ID]"
"[OPTION] on proposal [ID]"
```

**Examples**:
```
"Vote Approve on proposal 1"
"I vote Yes on proposal 5"
"Cast vote Against on proposal 3"
"For on proposal 2"
```

**Validation Rules**:
- Proposal must exist and be active
- Voting option must be valid for the proposal
- User cannot vote multiple times on same proposal
- Voting must occur before deadline

**Response Format**:
- Vote confirmation message
- Updated vote tallies
- Current proposal status

### Status Inquiry

**Purpose**: Retrieve current information about specific proposals

**Required Elements**:
- Proposal ID for status lookup

**Supported Patterns**:
```
"Status of proposal [ID]"
"What's the status of proposal [ID]?"
"How is proposal [ID] doing?"
"Results of proposal [ID]"
```

**Examples**:
```
"Status of proposal 1"
"What's the status of proposal 7?"
"How is proposal 3 doing?"
"Results of proposal 5"
```

**Response Information**:
- Proposal title and ID
- Complete vote breakdown with percentages
- Total participation count
- Current status (Active/Closed)
- Time remaining (for active proposals)

### Active Proposal Listing

**Purpose**: Display all proposals currently open for voting

**Supported Patterns**:
```
"Show active proposals"
"List all proposals"
"What can I vote on?"
"Active proposals"
```

**Response Format**:
- Numbered list of active proposals
- Basic vote counts for each
- Total number of active proposals
- Instructions for detailed status queries

### Help and Guidance

**Purpose**: Provide command examples and usage information

**Supported Patterns**:
```
"Help"
"What can you do?"
"How to use this?"
```

**Response Content**:
- Complete command reference
- Example usage for each function
- Tips for natural language interaction

## Interaction Guidelines

### Natural Language Processing

The agent uses pattern-matching algorithms optimized for governance terminology. While it accepts natural language input, including these key elements improves recognition accuracy:

**For Proposal Creation**:
- Use words like "create", "propose", "new proposal"
- Clearly state "with options" or "voting choices"
- Separate options with "and", "or", or commas

**For Voting**:
- Include "vote", "cast vote", or "I vote"
- Specify "on proposal [number]" or "for proposal [number]"
- Use exact option names as they appear in the proposal

**For Status Checks**:
- Include "status", "results", or "how is"
- Always specify the proposal number

### Error Handling

**Unrecognized Commands**:
When the agent cannot parse your intent, it will:
- Inform you that the command wasn't understood
- Provide examples of valid command patterns
- Suggest rephrasing your request

**Invalid Parameters**:
For commands with missing or invalid information:
- Specific error messages explaining what's missing
- Examples of correctly formatted commands
- Guidance on finding required information (like proposal IDs)

**System Errors**:
If blockchain communication fails:
- Clear error messages explaining the issue
- Suggestion to try again in a few moments
- No user data is lost during system errors

## System Limitations

### Functional Boundaries

**Governance-Specific Purpose**:
- Designed exclusively for proposal and voting management
- Cannot answer general questions or provide information outside governance scope
- Does not function as a general-purpose conversational AI

**No Proposal Execution**:
- Facilitates voting process only
- Does not automatically execute proposal outcomes
- Cannot manage funds, trigger actions, or modify system settings

**Stateless Interaction**:
- Each command is processed independently
- No memory of previous conversation context
- Cannot handle multi-turn conversations or follow-up questions without complete context

### Technical Constraints

**One Vote Per User**:
- Prevents duplicate voting through unique user identification
- No vote modification after submission
- Transparent vote attribution for audit purposes

**Proposal Immutability**:
- Proposals cannot be modified after creation
- Vote tallies are permanent and verifiable
- All governance data is stored permanently on blockchain

**Network Dependencies**:
- Requires active Internet Computer network connection
- Response times depend on blockchain network performance
- Temporary unavailability possible during network maintenance

## Best Practices

### Effective Communication

**Be Specific**:
- Include all required information in your initial command
- Use exact proposal IDs and option names
- Provide clear, concise proposal descriptions

**Use Consistent Language**:
- Stick to recognized command patterns when possible
- Reference proposals by their numeric IDs
- Use the exact voting option text as created

**Verify Actions**:
- Check proposal details before voting
- Confirm your vote was recorded correctly
- Review proposal status to understand current state

### Governance Participation

**Stay Informed**:
- Regularly check active proposals
- Review proposal details before voting
- Monitor results and participation rates

**Engage Responsibly**:
- Create clear, actionable proposals
- Provide sufficient context in proposal descriptions
- Choose appropriate voting options for your community's needs

## Troubleshooting

### Common Issues

**"I didn't understand that" Response**:
- Verify you're using supported command patterns
- Include all required elements (proposal ID, voting option, etc.)
- Try rephrasing using examples from this guide

**"Proposal not found" Error**:
- Confirm the proposal ID is correct
- Check if the proposal has closed or expired
- Use "show active proposals" to see available options

**"You have already voted" Message**:
- Each user can vote only once per proposal
- Vote changes are not permitted after submission
- Create a new proposal if voting options need modification

**Slow Response Times**:
- Network latency may cause delays during high usage
- Wait for complete responses before sending new commands
- Check Internet Computer network status if issues persist

### Getting Support

For technical issues beyond this guide:
- Review deployment documentation for system administrators
- Check project repository for known issues and updates
- Contact development team through official channels

## Advanced Usage

### Integration Opportunities

**Custom Interfaces**:
- Agent can integrate with custom chat interfaces
- API endpoints available for direct system integration
- Webhook support for external notification systems

**Governance Frameworks**:
- Suitable for any community governance needs
- Adaptable to various voting mechanisms and rules
- Extensible for custom proposal types and workflows

**Multi-Platform Deployment**:
- Works across different chat platforms and interfaces
- Consistent functionality regardless of access method
- Single governance system for multi-channel communities