import aiohttp
import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime, UTC

import cbor2
from ic.candid import encode, decode
from ic.principal import Principal

# Try to import IDL factory - fall back to JSON encoding if not available
try:
    from ic.candid import IDL, Types
    HAS_IDL = True
except ImportError:
    HAS_IDL = False
    logging.warning("IDL factory not available, using JSON encoding fallback")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
)

_LOG = logging.getLogger("canister_client")
_LOG.setLevel(logging.DEBUG)

class CanisterClient:
    """
    ICP HTTP-gateway client with proper JSON response parsing.
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

    def _parse_response_data(self, response_data):
        """Parse response data, handling both JSON strings and objects"""
        if isinstance(response_data, str):
            try:
                parsed = json.loads(response_data)
                logging.debug(f"Parsed JSON response: {parsed}")
                return parsed
            except json.JSONDecodeError:
                logging.debug("Response is not JSON, using as-is")
                return response_data
        return response_data

    @staticmethod
    def _encode_args_json_fallback(args: Any) -> bytes:
        """Fallback JSON encoding when IDL factory is not available"""
        logging.debug(f"_encode_args_json_fallback: args={args}, type={type(args)}")
        json_string = json.dumps(args, separators=(',', ':'))
        logging.debug(f"JSON encoded: {json_string}")
        return encode([json_string])

    async def _query_canister(self, method: str, encoded_args: bytes) -> Dict[str, Any]:
        try:
            logging.debug(f"_query_canister: method={method}")
            payload = {
                "request_type": "query",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": encoded_args,
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000),
            }
            envelope = cbor2.dumps({"content": payload})
            url = f"{self.boundary_node_url}/api/v2/canister/{self.canister_id}/query"
            logging.debug(f"POST {url}")

            session = await self._get_session()
            async with session.post(url, data=envelope) as resp:
                raw_data = await resp.read()
                logging.debug(f"HTTP status={resp.status}")
                if resp.status != 200:
                    error_text = await resp.text()
                    logging.error(f"Query error: {error_text}")
                    return {"success": False, "error": f"HTTP {resp.status}: {error_text}"}

                data = cbor2.loads(raw_data)
                logging.debug(f"CBOR loaded reply: {data}")

                if "replied" in data:
                    decoded = decode(data["replied"]["arg"])
                    logging.debug(f"Decoded canister reply: {decoded}, type={type(decoded)}")
                    
                    # Parse response data (handle JSON strings)
                    response_data = decoded[0] if decoded else None
                    parsed_data = self._parse_response_data(response_data)
                    
                    return {
                        "success": True,
                        "data": parsed_data,
                    }
                if "rejected" in data:
                    logging.error(f"Query rejected: {data['rejected']}")
                    return {"success": False, "error": data["rejected"]}
                logging.error("Unknown response format")
                return {"success": False, "error": "Unknown response format"}
        except asyncio.TimeoutError:
            logging.error("Timeout error")
            return {"success": False, "error": "Request timeout"}
        except Exception as exc:
            logging.exception("Exception in _query_canister")
            return {"success": False, "error": f"Network error: {exc}"}

    async def _update_canister(self, method: str, encoded_args: bytes) -> Dict[str, Any]:
        try:
            logging.debug(f"_update_canister: method={method}")
            payload = {
                "request_type": "call",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": encoded_args,
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000),
            }
            envelope = cbor2.dumps({"content": payload})
            url = f"{self.boundary_node_url}/api/v2/canister/{self.canister_id}/call"
            logging.debug(f"POST {url}")

            session = await self._get_session()
            async with session.post(url, data=envelope) as resp:
                raw_data = await resp.read()
                logging.debug(f"HTTP status={resp.status}")
                if resp.status == 202:
                    logging.debug("Update accepted")
                    # For updates, we might need to poll for the result
                    # For now, return a success message
                    return {"success": True, "data": "Update accepted"}
                error_text = await resp.text()
                logging.error(f"Call error: {error_text}")
                return {"success": False, "error": f"HTTP {resp.status}: {error_text}"}
        except asyncio.TimeoutError:
            logging.error("Timeout error")
            return {"success": False, "error": "Request timeout"}
        except Exception as exc:
            logging.exception("Exception in _update_canister")
            return {"success": False, "error": f"Network error: {exc}"}

    async def _call_canister_with_encoded_args(self, method: str, encoded_args: bytes, is_query: bool = True) -> Dict[str, Any]:
        """Call canister with pre-encoded arguments"""
        logging.debug(f"_call_canister_with_encoded_args: method={method}, is_query={is_query}")
        
        # Check if we're in local development mode
        if any(host in self.boundary_node_url for host in ("127.0.0.1", "localhost")):
            logging.debug("Calling mock response (local)")
            return await self._mock_response(method, {})
            
        if is_query:
            return await self._query_canister(method, encoded_args)
        else:
            return await self._update_canister(method, encoded_args)

    async def _mock_response(self, method: str, args: Any) -> Dict[str, Any]:
        logging.debug(f"_mock_response: method={method}")
        import random
        if method == "createProposal":
        # Return a proper result structure
            return {
                "success": True, 
                "data": {
                    "id": random.randint(1, 1000),
                    "status": "created"
                }
            }
        if method == "getActiveProposals":
            return {
                "success": True,
                "data": [
                    {"id": 1, "title": "Fund Marketing Campaign", "status": "Active"},
                    {"id": 2, "title": "Upgrade Infrastructure", "status": "Active"},
                ],
            }
        if method == "getProposalResults":
            return {"success": True, "data": [("For", 5), ("Against", 2)]}
        return {"success": False, "error": "Unknown method"}

    async def create_proposal(
        self,
        title: str,
        description: str,
        options: List[str],
        duration_hours: int,
        creator: str,
    ) -> Dict[str, Any]:
        logging.debug(f"create_proposal called with title='{title}', options={options}")
        
        # Use JSON encoding for simplicity
        args = {
            "request": {
                "title": title,
                "description": description,
                "options": options,
                "duration_hours": duration_hours,
            },
            "creator": creator
        }
        encoded_args = self._encode_args_json_fallback(args)
        logging.debug("Using JSON encoding")
        return await self._call_canister_with_encoded_args("createProposal", encoded_args, is_query=False)

    async def cast_vote(self, proposal_id: int, option: str, voter_id: str) -> Dict[str, Any]:
        logging.debug(f"cast_vote called for proposal {proposal_id}")
        
        args = {
            "proposal_id": proposal_id,
            "option": option,
            "voter_id": voter_id,
        }
        encoded_args = self._encode_args_json_fallback(args)
        return await self._call_canister_with_encoded_args("castVote", encoded_args, is_query=False)

    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        logging.debug(f"get_proposal called for proposal {proposal_id}")
        
        args = {"proposalId": proposal_id}
        encoded_args = self._encode_args_json_fallback(args)
        return await self._call_canister_with_encoded_args("getProposal", encoded_args, is_query=True)

    async def get_active_proposals(self) -> Dict[str, Any]:
        logging.debug("get_active_proposals called")
        
        args = {}
        encoded_args = self._encode_args_json_fallback(args)
        return await self._call_canister_with_encoded_args("getActiveProposals", encoded_args, is_query=True)

    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        logging.debug(f"get_proposal_results called for proposal {proposal_id}")
        
        args = {"proposalId": proposal_id}
        encoded_args = self._encode_args_json_fallback(args)
        return await self._call_canister_with_encoded_args("getProposalResults", encoded_args, is_query=True)

    async def close(self):
        if self.session:
            await self.session.close()
