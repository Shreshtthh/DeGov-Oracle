#!/usr/bin/env python3
"""
Integration test script for DeGov Oracle
Tests the full flow: canister <-> agent communication
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent', 'src'))

from canister_client import CanisterClient
from intents import IntentClassifier

async def test_integration():
    """Run integration tests"""
    print("🧪 Running DeGov Oracle Integration Tests...")
    
    # Initialize components
    canister_url = os.getenv('LOCAL_CANISTER_URL', 'http://127.0.0.1:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai')
    client = CanisterClient(canister_url)
    classifier = IntentClassifier()
    
    try:
        # Test 1: Intent Classification
        print("\n1. Testing Intent Classification...")
        
        test_messages = [
            "Create proposal: Fund the marketing campaign with options For and Against",
            "Vote For on proposal 1", 
            "What's the status of proposal 1?",
            "Show active proposals"
        ]
        
        for msg in test_messages:
            intent, params = classifier.classify(msg)
            print(f"   '{msg}' -> {intent}: {params}")
        
        # Test 2: Canister Communication
        print("\n2. Testing Canister Communication...")
        
        # Create a test proposal
        print("   Creating test proposal...")
        result = await client.create_proposal(
            title="Test Marketing Proposal",
            description="Should we fund the new marketing campaign?",
            options=["For", "Against"],
            duration_hours=72,
            creator="test-user"
        )
        
        if result['success']:
            proposal_id = result['data']
            print(f"   ✅ Created proposal #{proposal_id}")
            
            # Test voting
            print("   Testing vote casting...")
            vote_result = await client.cast_vote(
                proposal_id=proposal_id,
                option="For", 
                voter_id="test-voter-1"
            )
            
            if vote_result['success']:
                print("   ✅ Vote cast successfully")
            else:
                print(f"   ❌ Vote failed: {vote_result['error']}")
            
            # Test status check
            print("   Testing status check...")
            status_result = await client.get_proposal(proposal_id)
            
            if status_result['success']:
                proposal = status_result['data']
                print(f"   ✅ Retrieved proposal: {proposal['title']}")
            else:
                print(f"   ❌ Status check failed: {status_result['error']}")
                
        else:
            print(f"   ❌ Failed to create proposal: {result['error']}")
            
        # Test 3: List active proposals
        print("   Testing active proposals list...")
        active_result = await client.get_active_proposals()
        
        if active_result['success']:
            proposals = active_result['data']
            print(f"   ✅ Found {len(proposals)} active proposals")
        else:
            print(f"   ❌ Failed to get active proposals: {active_result['error']}")
            
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
    finally:
        await client.close()
    
    print("\n✅ Integration tests complete!")

if __name__ == "__main__":
    asyncio.run(test_integration())