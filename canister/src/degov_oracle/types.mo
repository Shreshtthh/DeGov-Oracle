import Time "mo:base/Time";
import HashMap "mo:base/HashMap";
import Text "mo:base/Text";

module Types {
    public type ProposalId = Nat;
    
    public type ProposalStatus = {
        #Active;
        #Closed;
    };
    
    public type Proposal = {
        id: ProposalId;
        title: Text;
        description: Text;
        options: [Text];
        votes: [(Text, Nat)]; // Changed from HashMap to array for easier serialization
        voters: [Text]; // Changed from Set to array
        created: Int;
        deadline: Int;
        status: ProposalStatus;
        creator: Text;
    };
    
    public type Vote = {
        proposal_id: ProposalId;
        voter: Text;
        option: Text;
        timestamp: Int;
    };
    
    public type CreateProposalRequest = {
        title: Text;
        description: Text;
        options: [Text];
        duration_hours: Nat;
    };
    
    public type VoteRequest = {
        proposal_id: ProposalId;
        option: Text;
        voter_id: Text;
    };
}