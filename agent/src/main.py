"""
DeGov-Oracle main.py
Implements the uAgents Chat Protocol for ASI:One compatibility
while preserving all original governance functionality.
"""

import os
import asyncio
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel                          # still used by utils/helpers
from uagents import Agent, Context, Protocol
from uagents.setup import fund_agent_if_low

# --- Chat-protocol primitives -----------------------------------------------
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

# --- Local modules -----------------------------------------------------------
from intents import IntentClassifier
from canister_client import CanisterClient
from utils import format_response, validate_input

# -----------------------------------------------------------------------------


# 1. Environment / deployment -------------------------------------------------
load_dotenv()

PORT = int(os.getenv("PORT", 8001))
ENDPOINT_URL = os.getenv("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{PORT}")

CANISTER_URL = (
    os.getenv("CANISTER_URL")
    or os.getenv("LOCAL_CANISTER_URL")
    or "http://localhost:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai"
)

agent = Agent(
    name=os.getenv("AGENT_NAME", "degov_oracle"),
    seed=os.getenv("AGENT_SEED", "degov-oracle-seed-12345"),
    port=PORT,
    endpoint=[f"{ENDPOINT_URL}/submit"],
    mailbox=True,        # required for Agentverse registration
)

# fund if necessary (ignore on testnets)
try:
    fund_agent_if_low(agent.wallet.address())
except Exception as e:
    print(f"[WARN] could not auto-fund wallet: {e}")

# 2. Core helpers -------------------------------------------------------------
intent_classifier = IntentClassifier()
canister_client = CanisterClient(CANISTER_URL)

# 3. Chat protocol implementation --------------------------------------------
chat_protocol = Protocol(spec=chat_protocol_spec)

@chat_protocol.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Main entry-point for ASI:One chat messages."""
    try:
        # --- acknowledge -----------------------------------------------------
        await ctx.send(
            sender,
            ChatAcknowledgement(
                timestamp=datetime.utcnow(),
                acknowledged_msg_id=msg.msg_id,
            ),
        )

        # --- extract user text ----------------------------------------------
        text = " ".join(
            item.text for item in msg.content if isinstance(item, TextContent)
        )
        ctx.logger.info(f"[chat] from {sender}: {text}")

        # --- validate & route ------------------------------------------------
        if not validate_input(text):
            response = (
                "Please provide a valid message. "
                "I can create proposals, cast votes, or check proposal status."
            )
        else:
            intent, params = intent_classifier.classify(text)
            ctx.logger.info(f"[intent] {intent} | {params}")

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
                response = (
                    "I didn't understand. Try: "
                    "'create a proposal', 'vote on proposal 1', "
                    "or 'show active proposals'."
                )

        # --- reply -----------------------------------------------------------
        await ctx.send(
            sender,
            ChatMessage(
                timestamp=datetime.utcnow(),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=format_response(response))],
            ),
        )

    except Exception as e:
        ctx.logger.error(f"[error] {e}")
        await ctx.send(
            sender,
            ChatMessage(
                timestamp=datetime.utcnow(),
                msg_id=uuid4(),
                content=[TextContent(type="text", text="Sorry, an error occurred.")],
            ),
        )

@chat_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"[ack] from {sender} for {msg.acknowledged_msg_id}")

# 4. Governance helpers (complete implementation) ----------------------------
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
            for proposal in proposals[:5]:
                votes_list = proposal.get('votes', [])
                total_votes = sum([count for opt, count in votes_list])
                proposal_list.append(f"#{proposal['id']}: {proposal['title']} ({total_votes} votes)")
            
            return f"📋 Active Proposals:\n\n" + "\n".join(proposal_list) + f"\n\nShowing {len(proposal_list)} proposals. Say 'status of proposal X' for details."
        else:
            return f"❌ Could not fetch proposals: {result['error']}"
            
    except Exception as e:
        ctx.logger.error(f"Error listing proposals: {str(e)}")
        return "Sorry, I couldn't fetch the active proposals. Please try again."

def get_help_message() -> str:
    return (
        "🤖 DeGov Oracle Help\n\n"
        "📝 Create proposals:  \"Create proposal: Fund marketing with options For, Against\"\n"
        "🗳️  Vote on proposals: \"Vote For on proposal 1\"\n"
        "📊 Check status:       \"What's the status of proposal 1?\"\n"
        "📋 List active:        \"Show active proposals\"\n\n"
        "Just talk to me naturally - I'll understand! 🚀"
    )

# 5. Health endpoint (unchanged except protocol list) -------------------------
@agent.on_event("startup")
async def startup(ctx: Context):
    try:
        if hasattr(ctx, "server") and hasattr(ctx.server, "_app"):
            async def health():
                return {
                    "status": "healthy",
                    "protocols": ["chat"],
                    "agent_address": agent.address,
                    "canister_url": CANISTER_URL,
                    "endpoint_url": ENDPOINT_URL,
                }
            ctx.server._app.add_api_route("/health", health, methods=["GET"])
            ctx.logger.info("Health endpoint mounted")
    except Exception as e:
        ctx.logger.warning(f"Health endpoint error: {e}")

    ctx.logger.info("DeGov Oracle Agent ready 🎉")
    ctx.logger.info(f"Agent address: {agent.address}")
    ctx.logger.info(f"Endpoint URL: {ENDPOINT_URL}")
    ctx.logger.info(f"Canister URL: {CANISTER_URL}")
    ctx.logger.info("Using Chat Protocol for ASI:One compatibility")

# 6. Register protocol & run --------------------------------------------------
agent.include(chat_protocol, publish_manifest=True)

if __name__ == "__main__":
    print(f"DeGov Oracle Agent starting...")
    print(f"Agent address: {agent.address}")
    print(f"Agent wallet: {agent.wallet.address()}")
    print(f"Registering with endpoint: {ENDPOINT_URL}/submit")
    print(f"Canister URL: {CANISTER_URL}")
    print(f"Using Chat Protocol for ASI:One compatibility")
    
    # Run the agent
    agent.run()