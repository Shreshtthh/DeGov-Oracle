import aiohttp
import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, Any, List

import cbor2
from ic.candid import encode, decode, Record, Text, Nat
from ic.principal import Principal

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
)

_LOG = logging.getLogger("canister_client")
_LOG.setLevel(logging.DEBUG)

class CanisterClient:
    """
    Minimal ICP HTTP-gateway client.
    Converts arbitrary python args → Candid bytes for Motoko canister calls.
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

    @staticmethod
    def _encode_args(args: Any) -> bytes:
        """Encode using Candid type wrappers to avoid KeyError 'type'"""
        logging.debug(f"_encode_args: args={args}, type={type(args)}")
        return encode(args)

    async def _query_canister(self, method: str, args: Any) -> Dict[str, Any]:
        try:
            logging.debug(f"_query_canister: method={method}, args={args}, type={type(args)}")
            payload = {
                "request_type": "query",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": self._encode_args(args),
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
                    return {
                        "success": True,
                        "data": decoded[0],
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

    async def _update_canister(self, method: str, args: Any) -> Dict[str, Any]:
        try:
            logging.debug(f"_update_canister: method={method}, args={args}, type={type(args)}")
            payload = {
                "request_type": "call",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": self._encode_args(args),
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

    async def _call_canister(self, method: str, args: Any, is_query: bool = True) -> Dict[str, Any]:
        logging.debug(f"_call_canister: method={method}, args={args}, type={type(args)} is_query={is_query}")
        if any(host in self.boundary_node_url for host in ("127.0.0.1", "localhost")):
            logging.debug("Calling mock response (local)")
            return await self._mock_response(method, args)
        if is_query:
            return await self._query_canister(method, args)
        else:
            return await self._update_canister(method, args)

    async def _mock_response(self, method: str, args: Any) -> Dict[str, Any]:
        logging.debug(f"_mock_response: method={method}, args={args}, type={type(args)}")
        import random
        if method == "createProposal":
            return {"success": True, "data": random.randint(1, 1000)}
        if method == "castVote":
            return {"success": True, "data": "Vote cast successfully"}
        if method == "getProposal":
            # Handle both Candid-wrapped and plain dict args
            if hasattr(args, 'get'):
                pid = args.get("proposalId", 1)
            else:
                pid = 1
            return {
                "success": True,
                "data": {
                    "id": pid,
                    "title": "Mock Proposal",
                    "description": "A mock proposal",
                    "status": "Active",
                    "votes": [("For", 3), ("Against", 1)],
                },
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
        # Use proper Candid type wrappers for Motoko canister
        request_record = Record({
            "title": Text(title),
            "description": Text(description),
            "options": [Text(opt) for opt in options],
            "duration_hours": Nat(duration_hours),
        })
        args = [request_record, Text(creator)]
        logging.debug(f"create_proposal: args={args}, type={type(args)}")
        return await self._call_canister("createProposal", args, is_query=False)

    async def cast_vote(self, proposal_id: int, option: str, voter_id: str) -> Dict[str, Any]:
        # Use proper Candid type wrappers for castVote
        vote_record = Record({
            "proposal_id": Nat(proposal_id),
            "option": Text(option),
            "voter_id": Text(voter_id),
        })
        args = [vote_record]
        logging.debug(f"cast_vote: args={args}, type={type(args)}")
        return await self._call_canister("castVote", args, is_query=False)

    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        args = [Nat(proposal_id)]
        logging.debug(f"get_proposal: args={args}")
        return await self._call_canister("getProposal", args, is_query=True)

    async def get_active_proposals(self) -> Dict[str, Any]:
        args = []  # No arguments needed
        logging.debug("get_active_proposals called")
        return await self._call_canister("getActiveProposals", args, is_query=True)

    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        args = [Nat(proposal_id)]
        logging.debug(f"get_proposal_results: args={args}")
        return await self._call_canister("getProposalResults", args, is_query=True)

    async def close(self):
        if self.session:
            await self.session.close()
