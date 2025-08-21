import aiohttp
import asyncio
import json
from typing import Dict, Any, List
import os

class CanisterClient:
    """Client for communicating with the ICP canister"""
    
    def __init__(self, canister_url: str):
        self.canister_url = canister_url.rstrip('/')
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"Content-Type": "application/json"}
            )
        return self.session
    
    async def _call_canister(self, method: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generic method to call canister functions"""
        try:
            session = await self._get_session()
            
            # Construct the URL for the canister method
            url = f"{self.canister_url}/api/v2/canister/{method}"
            
            payload = {
                "request_type": "call",
                "canister_id": self.canister_url.split('/')[-1].split('.')[0],
                "method_name": method,
                "arg": args
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "data": result}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
    
    async def create_proposal(self, title: str, description: str, options: List[str], 
                            duration_hours: int, creator: str) -> Dict[str, Any]:
        """Create a new proposal"""
        args = {
            "request": {
                "title": title,
                "description": description,
                "options": options,
                "duration_hours": duration_hours
            },
            "creator": creator
        }
        return await self._call_canister("createProposal", args)
    
    async def cast_vote(self, proposal_id: int, option: str, voter_id: str) -> Dict[str, Any]:
        """Cast a vote on a proposal"""
        args = {
            "request": {
                "proposal_id": proposal_id,
                "option": option,
                "voter_id": voter_id
            }
        }
        return await self._call_canister("castVote", args)
    
    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Get details of a specific proposal"""
        args = {"proposalId": proposal_id}
        return await self._call_canister("getProposal", args)
    
    async def get_active_proposals(self) -> Dict[str, Any]:
        """Get all active proposals"""
        return await self._call_canister("getActiveProposals", {})
    
    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        """Get results of a specific proposal"""
        args = {"proposalId": proposal_id}
        return await self._call_canister("getProposalResults", args)
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()