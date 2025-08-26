import aiohttp
import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, Any, List

import cbor2
from ic.candid import encode, decode
from ic.principal import Principal

_LOG = logging.getLogger("canister_client")
_LOG.setLevel(logging.INFO)


class CanisterClient:
    """
    Minimal ICP HTTP-gateway client.
    Converts arbitrary python args → JSON → Candid bytes
    so we don't need a full IDL schema during the hackathon.
    """

    def __init__(self, canister_url: str):
        # --- derive canisterId & boundary URL --------------------------------
        if "canisterId=" in canister_url:
            self.canister_id = canister_url.split("canisterId=")[1].split("&")[0]
            self.boundary_node_url = canister_url.split("?")[0]
        elif ".icp0.io" in canister_url:
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.boundary_node_url = "https://icp0.io"
        elif ".raw.icp0.io" in canister_url:
            self.canister_id = canister_url.split("://")[1].split(".")[0]
            self.boundary_node_url = "https://icp0.io"
        else:  # fallback: raw ID
            self.canister_id = canister_url
            self.boundary_node_url = "https://icp0.io"

        self.session: aiohttp.ClientSession | None = None

    # ---------------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------------
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/cbor"},
            )
        return self.session

    @staticmethod
    def _encode_args(args: Any) -> bytes:
        """
        Encode arbitrary python data to Candid without
        needing an explicit IDL schema.  Strategy:
           python → JSON str → encode([text])
        """
        wrapped = args if isinstance(args, (dict, list, tuple)) else [args]
        return encode([wrapped])

    # ---------------------------------------------------------------------
    # low-level query & update routes
    # ---------------------------------------------------------------------
    async def _query_canister(self, method: str, args: Any) -> Dict[str, Any]:
        try:
            payload = {
                "request_type": "query",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": self._encode_args(args),
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000),
            }
            envelope = cbor2.dumps({"content": payload})
            url = (
                f"{self.boundary_node_url}/api/v2/canister/"
                f"{self.canister_id}/query"
            )

            session = await self._get_session()
            async with session.post(url, data=envelope) as resp:
                if resp.status != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {resp.status}: {await resp.text()}",
                    }

                data = cbor2.loads(await resp.read())
                if "replied" in data:
                    return {
                        "success": True,
                        "data": decode(data["replied"]["arg"])[0],
                    }
                if "rejected" in data:
                    return {"success": False, "error": data["rejected"]}
                return {"success": False, "error": "Unknown response format"}
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as exc:
            _LOG.exception(exc)
            return {"success": False, "error": f"Network error: {exc}"}

    async def _update_canister(self, method: str, args: Any) -> Dict[str, Any]:
        try:
            payload = {
                "request_type": "call",
                "sender": Principal.anonymous(),
                "canister_id": Principal.from_str(self.canister_id),
                "method_name": method,
                "arg": self._encode_args(args),
                "ingress_expiry": int((time.time() + 300) * 1_000_000_000),
            }
            envelope = cbor2.dumps({"content": payload})
            url = (
                f"{self.boundary_node_url}/api/v2/canister/"
                f"{self.canister_id}/call"
            )

            session = await self._get_session()
            async with session.post(url, data=envelope) as resp:
                if resp.status == 202:
                    return {"success": True, "data": "Update accepted"}
                return {
                    "success": False,
                    "error": f"HTTP {resp.status}: {await resp.text()}",
                }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as exc:
            _LOG.exception(exc)
            return {"success": False, "error": f"Network error: {exc}"}

    # ---------------------------------------------------------------------
    # public helpers
    # ---------------------------------------------------------------------
    async def _call_canister(
        self, method: str, args: Any, is_query: bool = True
    ) -> Dict[str, Any]:
        # local dev short-circuit
        if any(host in self.boundary_node_url for host in ("127.0.0.1", "localhost")):
            return await self._mock_response(method, args)
        return (
            await self._query_canister(method, args)
            if is_query
            else await self._update_canister(method, args)
        )

    # ---------------------------------------------------------------------
    # mock endpoints for local tests
    # ---------------------------------------------------------------------
    async def _mock_response(self, method: str, args: Any) -> Dict[str, Any]:
        import random

        if method == "createProposal":
            return {"success": True, "data": random.randint(1, 1000)}
        if method == "castVote":
            return {"success": True, "data": "Vote cast successfully"}
        if method == "getProposal":
            pid = args.get("proposalId", 1)
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

    # ---------------------------------------------------------------------
    # DAO-specific helpers  ----------------------------------------------
    async def create_proposal(
        self,
        title: str,
        description: str,
        options: List[str],
        duration_hours: int,
        creator: str,
    ) -> Dict[str, Any]:
        args = {
            "title": title,
            "description": description,
            "options": options,
            "duration_hours": duration_hours,
            "creator": creator,
        }
        return await self._call_canister("createProposal", args, is_query=False)

    async def cast_vote(
        self, proposal_id: int, option: str, voter_id: str
    ) -> Dict[str, Any]:
        args = {"proposal_id": proposal_id, "option": option, "voter_id": voter_id}
        return await self._call_canister("castVote", args, is_query=False)

    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        return await self._call_canister(
            "getProposal", {"proposalId": proposal_id}, is_query=True
        )

    async def get_active_proposals(self) -> Dict[str, Any]:
        return await self._call_canister("getActiveProposals", {}, is_query=True)

    async def get_proposal_results(self, proposal_id: int) -> Dict[str, Any]:
        return await self._call_canister(
            "getProposalResults", {"proposalId": proposal_id}, is_query=True
        )

    # ---------------------------------------------------------------------
    async def close(self):
        if self.session:
            await self.session.close()
