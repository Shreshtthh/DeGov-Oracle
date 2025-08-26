import aiohttp
import asyncio
import json
from typing import Dict, Any, List
import os
import cbor2
from ic.candid import encode, decode
from ic.principal import Principal
import hashlib
import time

class CanisterClient:
    """Client for communicating with ICP canisters using proper HTTP Gateway Protocol"""
    
    def __init__(self, canister_url: str):
        # Extract canister ID from URL
        if "canisterId=" in canister_url:
            self.canister_id = canister_url.split("canisterId=")[1].split("&")[0]
            self.boundary_node_url = canister_url.split("?")[0]
        elif ".icp0.io" in canister_url:
            # Mainnet format: https://canister-id.icp0.io
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.boundary_node_url = "https://icp0.io"
        elif ".raw.icp0.io" in canister_url:
            # Raw mainnet format
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.boundary_node_url = "https://icp0.io"
        else:
            # Fallback - assume it's just the canister ID
            self.canister_id = canister_url
            self.boundary_node_url = "https://icp0.io"
            
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/cbor"}
            )
        return self.session
    
    async def _query_canister(self, method: str, args: Any) -> Dict[str, Any]:
        """Make a query call (read-only) to the canister"""
        try:
            session = await self._get_session()
            
            # Prepare the query payload
            query_payload = {
                "request_type": "query",
                "sender": Principal.anonymous(),  # For queries, anonymous sender is fine
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": encode([args]),  # Encode args using Candid
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000)  # 5 minutes from now
            }
            
            # Build the final payload with the request envelope
            request_envelope = cbor2.dumps({
                "content": query_payload
            })
            
            url = f"{self.boundary_node_url}/api/v2/canister/{self.canister_id}/query"
            
            async with session.post(url, data=request_envelope) as response:
                if response.status == 200:
                    response_data = cbor2.loads(await response.read())
                    
                    if "replied" in response_data:
                        # Decode the result from Candid
                        result_bytes = response_data["replied"]["arg"]
                        result = decode(result_bytes)
                        return {"success": True, "data": result[0]}
                    elif "rejected" in response_data:
                        return {"success": False, "error": f"Query rejected: {response_data['rejected']}"}
                    else:
                        return {"success": False, "error": "Unknown response format"}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
    
    async def _update_canister(self, method: str, args: Any) -> Dict[str, Any]:
        """Make an update call (state-changing) to the canister"""
        try:
            session = await self._get_session()
            
            # For update calls, we need to submit and then poll for the result
            # This is a simplified version - in production you'd want proper identity management
            
            # Generate a unique request ID
            request_id = hashlib.sha256(f"{method}{time.time()}".encode()).digest()
            
            # Prepare the update payload
            update_payload = {
                "request_type": "call",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": encode([args]),
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000),  # 5 minutes from now
            }
            
            # Build the final payload
            request_envelope = cbor2.dumps({
                "content": update_payload
            })
            
            # Submit the update call
            submit_url = f"{self.boundary_node_url}/api/v2/canister/{self.canister_id}/call"
            
            async with session.post(submit_url, data=request_envelope) as response:
                if response.status == 202:  # Accepted
                    # For hackathon purposes, we'll return success immediately
                    # In production, you'd poll for the result using the request_id
                    return {"success": True, "data": "Update call submitted successfully"}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
    
    # Helper method to choose between query and update
    async def _call_canister(self, method: str, args: Any, is_query: bool = True) -> Dict[str, Any]:
        """Generic method to call canister functions"""
        # Check if we're in local development mode
        if "127.0.0.1" in self.boundary_node_url or "localhost" in self.boundary_node_url:
            return await self._mock_response(method, args)
        
        if is_query:
            return await self._query_canister(method, args)
        else:
            return await self._update_canister(method, args)
    
    async def _mock_response(self, method: str, args: Any) -> Dict[str, Any]:
        """Mock responses for local development"""
        import random
        
        if method == "createProposal":
            proposal_id = random.randint(1, 1000)
            return {"success": True, "data": proposal_id}
        elif method == "castVote":
            return {"success": True, "data": "Vote cast successfully"}
        elif method == "getProposal":
            return {
                "success": True, 
                "data": {
                    "id": args.get("proposal_id", 1),
                    "title": "Mock Proposal",
                    "description": "This is a mock proposal for testing",
                    "status": "Active",
                    "votes": [("For", 3), ("Against", 1)]
                }
            }
        elif method == "getActiveProposals":
            return {
                "success": True, 
                "data": [
                    {
                        "id": 1,
                        "title": "Fund Marketing Campaign",
                        "description": "Should we allocate budget for marketing?",
                        "status": "Active",
                        "votes": [("For", 5), ("Against", 2)]
                    },
                    {
                        "id": 2,
                        "title": "Upgrade Infrastructure", 
                        "description": "Server upgrade proposal",
                        "status": "Active",
                        "votes": [("Yes", 3), ("No", 1)]
                    }
                ]
            }
        elif method == "getProposalResults":
            return {"success": True, "data": [("For", 5), ("Against", 2)]}
        else:
            return {"success": False, "error": "Unknown method"}
    
    async def create_proposal(self, title: str, description: str, options: List[str], 
                            duration_hours: int, creator: str) -> Dict[str, Any]:
        """Create a new proposal (update call)"""
        args = {
            "request": {
                "title": title,
                "description": description,
                "options": options,
                "duration_hours": duration_hours
            },
            "creator": creator
        }
        return await self._call_canister("createProposal", args, is_query=False)
    
    async def cast_vote(self, proposal_id: int, option: str, voter_id: str) -> Dict[str, Any]:
        """Cast a vote on a proposal (update call)"""
        args = {
            "request": {
                "proposal_id": proposal_id,
                "option": option,
                "voter_id": voter_id
            }
        }
        return await self._call_canister("castVote", args, is_query=False)
    
    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Get details of a specific proposal (query call)"""
        args = {"proposalId": proposal_id}
        return await self._call_canister("getProposal", args, is_query=True)
    
    async def get_active_proposals(self) -> Dict[str, Any]:
        """Get all active proposals (query call)"""
        return await self._call_canister("getActiveProposals", {}, is_query=True)
    
    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        """Get results of a specific proposal (query call)"""
        args = {"proposalId": proposal_id}
        return await self._call_canister("getProposalResults", args, is_query=True)
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()