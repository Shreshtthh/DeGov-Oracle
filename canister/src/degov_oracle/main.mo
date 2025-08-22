import Types "types";
import HashMap "mo:base/HashMap";
import Hash "mo:base/Hash";
import Array "mo:base/Array";
import Text "mo:base/Text";
import Time "mo:base/Time";
import Result "mo:base/Result";
import Debug "mo:base/Debug";
import Buffer "mo:base/Buffer";
import Iter "mo:base/Iter";
import Int "mo:base/Int";
import Nat "mo:base/Nat";

persistent actor DeGovOracle {
    // --- CORRECTED STATE ---
    // Use 'stable' for persistent state that survives upgrades
    var nextProposalId : Nat = 1;

    // For HashMap persistence, we need stable arrays and upgrade functions
    var proposalsEntries : [(Nat, Types.Proposal)] = [];
    private transient var proposals = HashMap.HashMap<Nat, Types.Proposal>(10, Nat.equal, Hash.hash);

    // --- UPGRADE FUNCTIONS ---
    // These are needed to persist HashMap data across upgrades
    system func preupgrade() {
        proposalsEntries := Iter.toArray(proposals.entries());
    };

    system func postupgrade() {
        proposals := HashMap.fromIter<Nat, Types.Proposal>(
            proposalsEntries.vals(), 
            proposalsEntries.size(), 
            Nat.equal, 
            Hash.hash
        );
        proposalsEntries := [];
    };

    private func hasVoted(voters: [Text], voterId: Text) : Bool {
        Array.find<Text>(voters, func(v) = v == voterId) != null
    };

    private func addVoter(voters: [Text], newVoter: Text) : [Text] {
        let buffer = Buffer.Buffer<Text>(voters.size() + 1);
        for (voter in voters.vals()) {
            buffer.add(voter);
        };
        buffer.add(newVoter);
        Buffer.toArray(buffer)
    };

    private func incrementVote(votes: [(Text, Nat)], option: Text) : [(Text, Nat)] {
        let buffer = Buffer.Buffer<(Text, Nat)>(votes.size());
        var found = false;
        
        for ((opt, count) in votes.vals()) {
            if (opt == option) {
                buffer.add((opt, count + 1));
                found := true;
            } else {
                buffer.add((opt, count));
            }
        };
        
        if (not found) {
            buffer.add((option, 1));
        };
        
        Buffer.toArray(buffer)
    };
    
    // --- PUBLIC FUNCTIONS ---
    public func createProposal(request: Types.CreateProposalRequest, creator: Text) : async Result.Result<Nat, Text> {
        let proposalId = nextProposalId;
        nextProposalId += 1;
        
        let now = Time.now();
        let deadline = now + (Int.abs(request.duration_hours) * 3600 * 1000000000);
        
        let votesBuffer = Buffer.Buffer<(Text, Nat)>(request.options.size());
        for (option in request.options.vals()) {
            votesBuffer.add((option, 0));
        };
        
        let proposal : Types.Proposal = {
            id = proposalId;
            title = request.title;
            description = request.description;
            options = request.options;
            votes = Buffer.toArray(votesBuffer);
            voters = [];
            created = now;
            deadline = deadline;
            status = #Active;
            creator = creator;
        };
        
        proposals.put(proposalId, proposal);
        #ok(proposalId)
    };
    
    public func castVote(request: Types.VoteRequest) : async Result.Result<Text, Text> {
        switch (proposals.get(request.proposal_id)) {
            case null { #err("Proposal not found") };
            case (?proposal) {
                if (proposal.status != #Active) {
                    return #err("Proposal is no longer active");
                };
                
                if (Time.now() > proposal.deadline) {
                    return #err("Voting deadline has passed");
                };
                
                if (hasVoted(proposal.voters, request.voter_id)) {
                    return #err("You have already voted on this proposal");
                };
                
                let validOption = Array.find<Text>(proposal.options, func(x) = x == request.option);
                switch (validOption) {
                    case null { #err("Invalid voting option") };
                    case (?_) {
                        let updatedVotes = incrementVote(proposal.votes, request.option);
                        let updatedVoters = addVoter(proposal.voters, request.voter_id);
                        
                        let updatedProposal : Types.Proposal = {
                            proposal with
                            votes = updatedVotes;
                            voters = updatedVoters;
                        };
                        
                        proposals.put(request.proposal_id, updatedProposal);
                        #ok("Vote cast successfully")
                    };
                };
            };
        };
    };
    
    public query func getProposal(proposalId: Nat) : async Result.Result<Types.Proposal, Text> {
        switch (proposals.get(proposalId)) {
            case null { #err("Proposal not found") };
            case (?proposal) { #ok(proposal) };
        };
    };
    
    public query func getActiveProposals() : async [Types.Proposal] {
        let allProposals = Iter.toArray(proposals.vals());
        Array.filter<Types.Proposal>(allProposals, func(p) = p.status == #Active)
    };
    
    public query func getProposalResults(proposalId: Nat) : async Result.Result<[(Text, Nat)], Text> {
        switch (proposals.get(proposalId)) {
            case null { #err("Proposal not found") };
            case (?proposal) {
                #ok(proposal.votes)
            };
        };
    };
    
    public func closeProposal(proposalId: Nat) : async Result.Result<Text, Text> {
        switch (proposals.get(proposalId)) {
            case null { #err("Proposal not found") };
            case (?proposal) {
                let updatedProposal : Types.Proposal = {
                    proposal with
                    status = #Closed;
                };
                proposals.put(proposalId, updatedProposal);
                #ok("Proposal closed successfully")
            };
        };
    };
}
