# Tranche Info

Actually more of a crowdsale summary

## Setup

1. Deploy your crowdsale (duh)
1. Dump the ABIs the JSON files
   ```
   solc --allow-paths . --combined-json abi contracts/AllocatedCrowdsale.sol > c.json
   solc --allow-paths . --combined-json abi contracts/BurnableCrowdsaleToken.sol > t.json
   solc --allow-paths . --combined-json abi contracts/TokenTranchePricing.sol > p.json
   solc --allow-paths . --combined-json abi contracts/GnosisWallet.sol > m.json
   ```
1. Ensure that an eth node is available on `127.0.0.1:8545`
1. Run, adding your Crowdsale address as the only argument
   ```
   ./tranche_info.py 0x852A2f89F4AdBAc5707e73eE576b6B268e59aa75
   ```
