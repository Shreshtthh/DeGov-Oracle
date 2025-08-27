import aiohttp
import asyncio
import logging
import time
from typing import Dict, Any, List

import cbor2
from ic.candid import IDL, Types, encode, decode
from ic.principal import Principal

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
)

_LOG = logging.getLogger("canister_client")
_LOG.setLevel(logging.DEBUG)

class CanisterClient:
    """
    ICP HTTP-gateway client with proper IDL factory support for type-safe
    communication with the Motoko canister. Includes mock responses for local testing.
    """

    def __init__(self, canister_url: str):
        if "canisterId=" in canister_url:
            self.canister_id = canister_url.split("canisterId=")[1].split("&")[0]
            self.boundary_node_url = canister_url.split("?")[0]
        elif ".icp0.io" in canister_url:
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.boundary_node_url = "https://icp0.io"
        elif ".raw.icp0.io" in canister_url:
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.boundary_node_url = "https://icp0.io"
        else:
            self.canister_id = canister_url
            self.boundary_node_url = "https://icp0.io"
        self.session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/cbor"},
            )
        return self.session

    async def _mock_response(self, method: str) -> Dict[str, Any]:
        """Mock responses for local testing"""
        import random
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
        """Generic method to call canister functions with pre-encoded args."""
        if "127.0.0.1" in self.boundary_node_url or "localhost" in self.boundary_node_url:
            return await self._mock_response(method)

        try:
            request_type = "query" if is_query else "call"
            url = f"{self.boundary_node_url}/api/v2/canister/{self.canister_id}/{request_type}"

            payload = {
                "request_type": request_type,
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": encoded_args,
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000),
            }
            envelope = cbor2.dumps({"content": payload})

            session = await self._get_session()
            async with session.post(url, data=envelope) as resp:
                raw_data = await resp.read()
                logging.debug(f"HTTP status={resp.status} for method {method}")

                if resp.status == 202 and not is_query:
                    return {"success": True, "data": "Update accepted"}

                if resp.status != 200:
                    error_text = await resp.text()
                    logging.error(f"HTTP error {resp.status}: {error_text}")
                    return {"success": False, "error": f"HTTP {resp.status}: {error_text}"}

                # Parse CBOR response
                try:
                    data = cbor2.loads(raw_data)
                    logging.debug(f"Parsed CBOR data: {data}")
                except Exception as e:
                    logging.error(f"Failed to parse CBOR data: {e}")
                    return {"success": False, "error": f"CBOR parsing error: {e}"}

                # Handle different response types
                if isinstance(data, dict):
                    if "replied" in data:
                        try:
                            # Ensure we have bytes for decode
                            arg_data = data["replied"]["arg"]
                            if isinstance(arg_data, str):
                                # If it's a string, it might be base64 encoded
                                import base64
                                try:
                                    arg_data = base64.b64decode(arg_data)
                                except Exception:
                                    logging.error(f"Failed to decode base64 arg: {arg_data}")
                                    return {"success": False, "error": "Invalid arg format"}
                            
                            # Decode the candid result
                            decoded_result = decode(arg_data)
                            logging.debug(f"Decoded result: {decoded_result}")
                            
                            # Handle the decoded result
                            if isinstance(decoded_result, (list, tuple)) and len(decoded_result) > 0:
                                result = decoded_result[0]
                            else:
                                result = decoded_result
                            
                            # Check for Ok/Err pattern
                            if isinstance(result, dict):
                                if "Ok" in result:
                                    return {"success": True, "data": result["Ok"]}
                                elif "Err" in result:
                                    return {"success": False, "error": result["Err"]}
                            
                            return {"success": True, "data": result}
                            
                        except Exception as e:
                            logging.error(f"Failed to decode candid data: {e}")
                            logging.error(f"Raw arg data type: {type(data['replied']['arg'])}")
                            logging.error(f"Raw arg data: {data['replied']['arg']}")
                            return {"success": False, "error": f"Candid decode error: {e}"}

                    elif "rejected" in data:
                        error_info = data["rejected"]
                        logging.error(f"Request rejected: {error_info}")
                        return {"success": False, "error": f"Request rejected: {error_info}"}
                    
                    elif "status" in data:
                        # Handle status responses for update calls
                        status = data["status"]
                        if status == "replied":
                            return {"success": True, "data": "Update completed"}
                        elif status == "rejected":
                            return {"success": False, "error": "Update rejected"}
                        else:
                            return {"success": True, "data": f"Status: {status}"}
                
                # If we get here, we have an unexpected response format
                logging.warning(f"Unknown response format: {data}")
                return {"success": False, "error": f"Unknown response format: {type(data)}"}

        except Exception as exc:
            logging.exception(f"Exception in _call_canister for method {method}")
            return {"success": False, "error": f"Network error: {exc}"}

    async def create_proposal(self, title: str, description: str, options: List[str], duration_hours: int, creator: str) -> Dict[str, Any]:
        ProposalRequest = IDL.Record({
            "title": Types.Text, "description": Types.Text,
            "options": Types.Vec(Types.Text), "duration_hours": Types.Nat,
        })
        request_data = {"title": title, "description": description, "options": options, "duration_hours": duration_hours}
        encoded_args, = IDL.encode([ProposalRequest, Types.Text], [request_data, creator])
        return await self._call_canister("createProposal", encoded_args, is_query=False)

    async def cast_vote(self, proposal_id: int, option: str, voter_id: str) -> Dict[str, Any]:
        VoteRequest = IDL.Record({"proposal_id": Types.Nat, "option": Types.Text, "voter_id": Types.Text})
        request_data = {"proposal_id": proposal_id, "option": option, "voter_id": voter_id}
        encoded_args, = IDL.encode([VoteRequest], [request_data])
        return await self._call_canister("castVote", encoded_args, is_query=False)

    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        encoded_args, = IDL.encode([Types.Nat], [proposal_id])
        return await self._call_canister("getProposal", encoded_args, is_query=True)

    async def get_active_proposals(self) -> Dict[str, Any]:
        encoded_args, = IDL.encode([], [])
        return await self._call_canister("getActiveProposals", encoded_args, is_query=True)

    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        encoded_args, = IDL.encode([Types.Nat], [proposal_id])
        return await self._call_canister("getProposalResults", encoded_args, is_query=True)

    async def close(self):
        if self.session:
            await self.session.close()