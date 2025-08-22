import asyncio
import os
from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low
from pydantic import BaseModel

from intents import IntentClassifier
from canister_client import CanisterClient
from utils import format_response, validate_input

# Load environment variables
load_dotenv()

# Initialize agent with proper endpoint configuration
agent = Agent(
    name=os.getenv("AGENT_NAME", "degov_oracle"),
    seed=os.getenv("AGENT_SEED", "default-seed"),
    port=int(os.getenv("AGENT_PORT", 8001)),
    endpoint=[f"http://localhost:{os.getenv('AGENT_PORT', 8001)}/submit"]  # Add endpoint
)

# Fund agent if needed (this also helps with registration)
fund_agent_if_low(agent.wallet.address())

# Initialize components
intent_classifier = IntentClassifier()
canister_client = CanisterClient(
    canister_url=os.getenv("CANISTER_URL") or os.getenv("LOCAL_CANISTER_URL")
)

# Define a simple Pydantic model for string messages
class Message(BaseModel):
    message: str

# Chat protocol for ASI:One
chat_protocol = Protocol("DeGov Chat")

@chat_protocol.on_message(model=Message)
async def handle_message(ctx: Context, sender: str, msg: Message):
    """Main message handler"""
    try:
        # Log incoming message
        ctx.logger.info(f"Received message from {sender}: {msg.message}")
        
        # Validate input
        if not validate_input(msg.message):
            await ctx.send(sender, Message(message="Please provide a valid message. I can help you create proposals, vote, or check proposal status."))
            return
        
        # Classify intent and extract parameters
        intent, params = intent_classifier.classify(msg.message)
        ctx.logger.info(f"Classified intent: {intent}, params: {params}")
        
        # Route to appropriate handler
        if intent == "CREATE_PROPOSAL":
            response = await handle_create_proposal(ctx, params, sender)
        elif intent == "CAST_VOTE":
            response = await handle_cast_vote(ctx, params, sender)
        elif intent == "CHECK_STATUS":
            response = await handle_check_status(ctx, params)
        elif intent == "LIST_ACTIVE":
            response = await handle_list_active(ctx)
        elif intent == "HELP":
            response = get_help_message()
        else:
            response = "I didn't understand that. Try saying something like 'create a proposal' or 'show active proposals'."
        
        # Send formatted response
        formatted_response = format_response(response)
        await ctx.send(sender, Message(message=formatted_response))
        
    except Exception as e:
        ctx.logger.error(f"Error handling message: {str(e)}")
        await ctx.send(sender, Message(message="Sorry, I encountered an error. Please try again."))

async def handle_create_proposal(ctx: Context, params: dict, creator: str):
    """Handle proposal creation"""
    try:
        if not all(k in params for k in ['title', 'description', 'options']):
            return "To create a proposal, I need: title, description, and voting options. Try: 'Create proposal: Fund marketing campaign with options For and Against'"
        
        result = await canister_client.create_proposal(
            title=params['title'],
            description=params['description'],
            options=params['options'],
            duration_hours=params.get('duration_hours', 72),
            creator=creator
        )
        
        if result['success']:
            proposal_id = result['data']
            return f"✅ Proposal #{proposal_id} created successfully!\n\nTitle: {params['title']}\nVoting is now open for 72 hours."
        else:
            return f"❌ Failed to create proposal: {result['error']}"
            
    except Exception as e:
        ctx.logger.error(f"Error creating proposal: {str(e)}")
        return "Sorry, I couldn't create the proposal. Please try again."

async def handle_cast_vote(ctx: Context, params: dict, voter: str):
    """Handle vote casting"""
    try:
        if not all(k in params for k in ['proposal_id', 'option']):
            return "To vote, I need the proposal ID and your choice. Try: 'Vote For on proposal 1'"
        
        result = await canister_client.cast_vote(
            proposal_id=params['proposal_id'],
            option=params['option'],
            voter_id=voter
        )
        
        if result['success']:
            # Get updated proposal status
            status_result = await canister_client.get_proposal(params['proposal_id'])
            if status_result['success']:
                proposal = status_result['data']
                # Handle votes as list of tuples from Motoko
                votes_list = proposal.get('votes', [])
                vote_summary = ", ".join([f"{opt}: {count}" for opt, count in votes_list])
                return f"✅ Vote cast successfully!\n\nProposal #{params['proposal_id']} current results:\n{vote_summary}"
            else:
                return "✅ Vote cast successfully!"
        else:
            return f"❌ Failed to cast vote: {result['error']}"
            
    except Exception as e:
        ctx.logger.error(f"Error casting vote: {str(e)}")
        return "Sorry, I couldn't cast your vote. Please try again."

async def handle_check_status(ctx: Context, params: dict):
    """Handle status checks"""
    try:
        proposal_id = params.get('proposal_id')
        if not proposal_id:
            return "Please specify which proposal you'd like to check. Try: 'What's the status of proposal 1?'"
        
        result = await canister_client.get_proposal(proposal_id)
        
        if result['success']:
            proposal = result['data']
            # Handle votes as list of tuples from Motoko
            votes_list = proposal.get('votes', [])
            vote_summary = "\n".join([f"  {opt}: {count} votes" for opt, count in votes_list])
            total_votes = sum([count for opt, count in votes_list])
            
            status_emoji = "🟢" if proposal.get('status') == 'Active' else "🔴"
            
            return f"{status_emoji} Proposal #{proposal['id']}: {proposal['title']}\n\nResults ({total_votes} total votes):\n{vote_summary}\n\nStatus: {proposal['status']}"
        else:
            return f"❌ Could not find proposal: {result['error']}"
            
    except Exception as e:
        ctx.logger.error(f"Error checking status: {str(e)}")
        return "Sorry, I couldn't check the proposal status. Please try again."

async def handle_list_active(ctx: Context):
    """Handle listing active proposals"""
    try:
        result = await canister_client.get_active_proposals()
        
        if result['success']:
            proposals = result['data']
            if not proposals:
                return "📝 No active proposals at the moment. Would you like to create one?"
            
            proposal_list = []
            for proposal in proposals[:5]:  # Limit to 5 for chat readability
                # Handle votes as list of tuples from Motoko
                votes_list = proposal.get('votes', [])
                total_votes = sum([count for opt, count in votes_list])
                proposal_list.append(f"#{proposal['id']}: {proposal['title']} ({total_votes} votes)")
            
            return f"📋 Active Proposals:\n\n" + "\n".join(proposal_list) + f"\n\nShowing {len(proposal_list)} proposals. Say 'status of proposal X' for details."
        else:
            return f"❌ Could not fetch proposals: {result['error']}"
            
    except Exception as e:
        ctx.logger.error(f"Error listing proposals: {str(e)}")
        return "Sorry, I couldn't fetch the active proposals. Please try again."

def get_help_message():
    """Return help message"""
    return """🤖 DeGov Oracle Help

I can help you with DAO governance:

📝 Create proposals:
"Create proposal: Fund marketing with options For, Against"

🗳️  Vote on proposals:
"Vote For on proposal 1"

📊 Check status:
"What's the status of proposal 1?"

📋 List active proposals:
"Show active proposals"

Just talk to me naturally - I'll understand! 🚀"""

# Register the protocol with the agent
agent.include(chat_protocol)

# Add startup event to ensure registration
@agent.on_event("startup")
async def startup_event(ctx: Context):
    """Handle startup tasks"""
    ctx.logger.info(f"DeGov Oracle Agent started!")
    ctx.logger.info(f"Agent address: {agent.address}")
    ctx.logger.info(f"Agent wallet: {agent.wallet.address()}")

if __name__ == "__main__":
    print(f"DeGov Oracle Agent starting...")
    print(f"Agent address: {agent.address}")
    print(f"Agent wallet: {agent.wallet.address()}")
    
    # Run the agent
    agent.run()