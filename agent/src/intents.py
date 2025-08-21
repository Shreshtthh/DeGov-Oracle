import re
from typing import Tuple, Dict, Any, Optional

class IntentClassifier:
    """Simple but effective intent classification for governance actions"""
    
    def __init__(self):
        self.create_patterns = [
            r"create\s+proposal",
            r"new\s+proposal", 
            r"propose\s+",
            r"submit\s+proposal"
        ]
        
        self.vote_patterns = [
            r"vote\s+(\w+)\s+on\s+proposal\s+(\d+)",
            r"i\s+vote\s+(\w+)",
            r"cast\s+vote\s+(\w+)",
            r"(\w+)\s+on\s+proposal\s+(\d+)"
        ]
        
        self.status_patterns = [
            r"status\s+of\s+proposal\s+(\d+)",
            r"proposal\s+(\d+)\s+status",
            r"how\s+is\s+proposal\s+(\d+)",
            r"results\s+of\s+proposal\s+(\d+)"
        ]
        
        self.list_patterns = [
            r"what\s+can\s+i\s+vote",
            r"active\s+proposals",
            r"show\s+proposals",
            r"list\s+proposals"
        ]
        
        self.help_patterns = [
            r"help",
            r"what\s+can\s+you\s+do",
            r"how\s+to\s+use"
        ]
    
    def classify(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """Classify user intent and extract parameters"""
        msg_lower = message.lower().strip()
        
        # Check for help
        if self._matches_patterns(msg_lower, self.help_patterns):
            return "HELP", {}
        
        # Check for create proposal
        if self._matches_patterns(msg_lower, self.create_patterns):
            params = self._extract_proposal_details(message)
            return "CREATE_PROPOSAL", params
        
        # Check for voting
        vote_params = self._extract_vote_details(msg_lower)
        if vote_params:
            return "CAST_VOTE", vote_params
        
        # Check for status
        status_params = self._extract_status_details(msg_lower)
        if status_params:
            return "CHECK_STATUS", status_params
        
        # Check for list active
        if self._matches_patterns(msg_lower, self.list_patterns):
            return "LIST_ACTIVE", {}
        
        return "UNKNOWN", {}
    
    def _matches_patterns(self, text: str, patterns: list) -> bool:
        """Check if text matches any pattern in the list"""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    def _extract_proposal_details(self, message: str) -> Dict[str, Any]:
        """Extract proposal creation details"""
        # Look for title after "proposal:"
        title_match = re.search(r"proposal:?\s+([^,\n]+)", message, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Untitled Proposal"
        
        # Look for description
        desc_match = re.search(r"description:?\s+([^,\n]+)", message, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else title
        
        # Look for options
        options_match = re.search(r"options?\s+([^,\n]+)", message, re.IGNORECASE)
        if options_match:
            options_text = options_match.group(1)
            # Split by common separators
            options = [opt.strip() for opt in re.split(r'[,\s]+and\s+|\s+or\s+|,', options_text)]
            options = [opt for opt in options if opt]  # Remove empty strings
        else:
            # Default options
            options = ["For", "Against"]
        
        return {
            "title": title,
            "description": description,
            "options": options,
            "duration_hours": 72  # Default 3 days
        }
    
    def _extract_vote_details(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract voting details"""
        # Pattern: "vote [option] on proposal [id]"
        match = re.search(r"vote\s+(\w+)\s+on\s+proposal\s+(\d+)", message, re.IGNORECASE)
        if match:
            return {
                "option": match.group(1).title(),
                "proposal_id": int(match.group(2))
            }
        
        # Pattern: "[option] on proposal [id]"
        match = re.search(r"(\w+)\s+on\s+proposal\s+(\d+)", message, re.IGNORECASE)
        if match and match.group(1).lower() in ['for', 'against', 'yes', 'no']:
            return {
                "option": match.group(1).title(),
                "proposal_id": int(match.group(2))
            }
        
        return None
    
    def _extract_status_details(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract proposal ID for status checks"""
        match = re.search(r"proposal\s+(\d+)", message, re.IGNORECASE)
        if match:
            return {"proposal_id": int(match.group(1))}
        return None