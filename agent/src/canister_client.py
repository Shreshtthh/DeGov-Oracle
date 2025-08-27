import asyncio
import logging
import time
from typing import Dict, Any, List
import random

from ic.client import Client
from ic.identity import Identity
from ic.agent import Agent as IcAgent
from ic.candid import Types, encode, decode

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
)

_LOG = logging.getLogger("canister_client")
_LOG.setLevel(logging.DEBUG)

class CanisterClient:
    """
    ICP client using the ic-py Agent API for type-safe communication with canisters.
    Includes mock responses for local testing.
    """

    def __init__(self, canister_url: str):
        # Parse canister URL to extract canister ID
        if "canisterId=" in canister_url:
            self.canister_id = canister_url.split("canisterId=")[1].split("&")[0]
            self.is_local = "127.0.0.1" in canister_url or "localhost" in canister_url
        elif ".icp0.io" in canister_url:
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.is_local = False
        elif ".raw.icp0.io" in canister_url:
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.is_local = False
        else:
            # Assume it's a plain canister ID
            self.canister_id = canister_url
            self.is_local = "127.0.0.1" in canister_url or "localhost" in canister_url
        
        # Initialize IC Agent
        self.identity = Identity()
        
        if self.is_local:
            self.client = Client(url="http://127.0.0.1:4943")
        else:
            self.client = Client(url="https://ic0.app")
            
        self.ic_agent = IcAgent(self.identity, self.client)

    async def _mock_response(self, method: str) -> Dict[str, Any]:
        """Mock responses for local testing"""
        if method == "createProposal":
            return {"success": True, "data": random.randint(1, 1000)}
        elif method == "getProposal":
            return {
                "success": True,
                "data": {
                    "id": 1,
                    "title": "Mock Proposal",
                    "description": "A mock proposal for testing",
                    "status": {"Active": None},
                    "votes": [("For", 3), ("Against", 1)],
                }
            }
        elif method == "getActiveProposals":
            return {
                "success": True,
                "data": [
                    {"id": 1, "title": "Mock Proposal 1", "status": {"Active": None}},
                    {"id": 2, "title": "Mock Proposal 2", "status": {"Active": None}},
                ]
            }
        elif method == "castVote":
            return {"success": True, "data": "Vote cast successfully"}
        elif method == "getProposalResults":
            return {"success": True, "data": [("For", 5), ("Against", 2)]}
        return {"success": False, "error": "Unknown method"}

    async def _call_canister(self, method: str, encoded_args: bytes, is_query: bool) -> Dict[str, Any]:
        """Generic method to call canister functions."""
        # Use mocks for local testing if needed
        if self.is_local and "mock" in method.lower():
            return await self._mock_response(method)

        try:
            if is_query:
                result_bytes = self.ic_agent.query_raw(self.canister_id, method, encoded_args)
                logging.debug(f"Query result for {method}: {result_bytes}")
                return {"success": True, "data": result_bytes}
            else:
                result = self.ic_agent.update_raw(self.canister_id, method, encoded_args)
                logging.debug(f"Update result for {method}: {result}")
                return {"success": True, "data": result}

        except Exception as exc:
            logging.exception(f"Exception in _call_canister for method {method}")
            return {"success": False, "error": f"Canister call error: {exc}"}

    async def create_proposal(self, title: str, description: str, options: List[str], duration_hours: int, creator: str) -> Dict[str, Any]:
        """Create a new proposal"""
        try:
            # Encode the proposal request as a record
            proposal_data = {
                "title": title,
                "description": description, 
                "options": options,
                "duration_hours": duration_hours
            }
            
            # Encode parameters following your working pattern
            encoded_args = encode([
                {
                    "type": Types.Record({
                        "title": Types.Text,
                        "description": Types.Text,
                        "options": Types.Vec(Types.Text),
                        "duration_hours": Types.Nat,
                    }),
                    "value": proposal_data
                },
                {"type": Types.Text, "value": creator}
            ])
            
            return await self._call_canister("createProposal", encoded_args, is_query=False)
        except Exception as e:
            logging.error(f"Error in create_proposal: {e}")
            return {"success": False, "error": str(e)}

    async def cast_vote(self, proposal_id: int, option: str, voter_id: str) -> Dict[str, Any]:
        """Cast a vote on a proposal"""
        try:
            vote_data = {
                "proposal_id": proposal_id,
                "option": option,
                "voter_id": voter_id
            }
            
            encoded_args = encode([{
                "type": Types.Record({
                    "proposal_id": Types.Nat,
                    "option": Types.Text,
                    "voter_id": Types.Text,
                }),
                "value": vote_data
            }])
            
            return await self._call_canister("castVote", encoded_args, is_query=False)
        except Exception as e:
            logging.error(f"Error in cast_vote: {e}")
            return {"success": False, "error": str(e)}

    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Get a specific proposal by ID"""
        try:
            encoded_args = encode([{"type": Types.Nat, "value": proposal_id}])
            return await self._call_canister("getProposal", encoded_args, is_query=True)
        except Exception as e:
            logging.error(f"Error in get_proposal: {e}")
            return {"success": False, "error": str(e)}

    async def get_active_proposals(self) -> Dict[str, Any]:
        """Get all active proposals"""
        try:
            # Empty args for methods with no parameters
            encoded_args = encode([])
            return await self._call_canister("getActiveProposals", encoded_args, is_query=True)
        except Exception as e:
            logging.error(f"Error in get_active_proposals: {e}")
            return {"success": False, "error": str(e)}

    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        """Get results for a specific proposal"""
        try:
            encoded_args = encode([{"type": Types.Nat, "value": proposal_id}])
            return await self._call_canister("getProposalResults", encoded_args, is_query=True)
        except Exception as e:
            logging.error(f"Error in get_proposal_results: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Clean up resources (placeholder for compatibility)"""
        pass

# Example usage matching your working pattern:
async def example_usage():
    """Example showing how to use the canister client"""
    client = CanisterClient("your-canister-id-here")
    
    # Create a proposal
    result = await client.create_proposal(
        title="Test Proposal",
        description="A test proposal",
        options=["Approve", "Reject"], 
        duration_hours=72,
        creator="test-user"
    )
    print(f"Create proposal result: {result}")
    
    # Get active proposals
    proposals = await client.get_active_proposals()
    print(f"Active proposals: {proposals}")
    
    await client.close()