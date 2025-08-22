#!/bin/bash

echo "🚀 Deploying DeGov Oracle Canister..."

cd canister

# Start local dfx if not running
if ! dfx ping local > /dev/null 2>&1; then
    echo "Starting local dfx..."
    dfx start --background --clean
fi

# Install dependencies
echo "Installing Motoko dependencies..."
vessel install

# Deploy locally first
echo "Deploying to local network..."
dfx deploy --network local

# Get canister ID
LOCAL_CANISTER_ID=$(dfx canister id degov_oracle --network local)
echo "Local Canister ID: $LOCAL_CANISTER_ID"
echo "Local URL: http://127.0.0.1:4943/?canisterId=$LOCAL_CANISTER_ID"

# Update .env file
cd ../agent
sed -i "s/your-local-canister-id/$LOCAL_CANISTER_ID/g" .env

echo "✅ Local deployment complete!"
echo "To deploy to mainnet, run: dfx deploy --network ic"