#!/usr/bin/env python3

import json
import sys

import crayons
import web3

from eth_utils import from_wei, to_wei
from tabulate import tabulate


def num_disp(value):
    return '{:,f}'.format(value)


if len(sys.argv) != 2:
    raise Exception('Must give the Crowdsale address as the only argument')


abi_names = dict(
    c = 'AllocatedCrowdsale.sol:AllocatedCrowdsale',
    t = 'BurnableCrowdsaleToken.sol:BurnableCrowdsaleToken',
    p = 'TokenTranchePricing.sol:TokenTranchePricing',
    m = 'GnosisWallet.sol:MultiSigWallet',
)
addresses = dict(
    c = sys.argv[-1],
)
address_get_names = dict(
    t = 'token',
    p = 'pricingStrategy',
    m = 'multisigWallet',
)
contracts = {}


w = web3.Web3(web3.providers.rpc.HTTPProvider('http://127.0.0.1:8545'))


ordered_parse = ['c']
most_keys = set(abi_names.keys())
most_keys.remove('c')
ordered_parse.extend(most_keys)


for key in ordered_parse:
    name = abi_names[key]
    with open('%s.json' % key) as handle:
        meta = json.load(handle)
        abi = json.loads(meta['contracts']['contracts/%s' % name]['abi'])
        contracts[key] = w.eth.contract(abi)

        if key in addresses:
            contracts[key].address = addresses[key]
        else:
            contracts[key].address = getattr(contracts['c'].call(), address_get_names[key])()


tokens_sold = contracts['c'].call().tokensSold()
tokens_remain = contracts['t'].call().allowance(contracts['m'].address, contracts['c'].address)
tokens_total = tokens_sold + tokens_remain
wei_raised = contracts['c'].call().weiRaised()
tranche_idx = contracts['p'].call().getCurrentTrancheIdx(tokens_sold)
tranche_min_tx = contracts['c'].call().trancheMinTx()
multisig_wei = w.eth.getBalance(contracts['m'].address)


tranches = []
idx = 0
wei_price = None
while wei_price is None or wei_price > 0:
    chk_amount, wei_price = contracts['p'].call().tranches(idx)
    tranches.append(dict(chk_lim = chk_amount, wei = wei_price))
    idx += 1

for idx, tranche in enumerate(tranches):
    if tranche['wei'] == 0:
        continue
    real_next_lim = min(tranches[idx + 1]['chk_lim'], tokens_total)
    tranche['chk_vol'] = real_next_lim - tranche['chk_lim']


# Last tranche is bogus
tranches.pop()


print(crayons.yellow('Summary'))
print(tabulate([
    ['VDOC total', num_disp(from_wei(tokens_total, 'ether'))],
    ['VDOC sold', num_disp(from_wei(tokens_sold, 'ether'))],
    ['VDOC remain', num_disp(from_wei(tokens_remain, 'ether'))],
    ['ETH raised', num_disp(from_wei(wei_raised, 'ether'))],
    ['MultiSig ETH', num_disp(from_wei(multisig_wei, 'ether'))],
]))


for idx, tranche in enumerate(tranches):
    print()
    head = 'Tranche {num} {current}'.format(
        num = idx + 1,
        current = '- CURRENT' if idx == tranche_idx else '',
    )
    head = crayons.green(head) if idx == tranche_idx else crayons.red(head)
    print(head)
    eth_total = from_wei(tranche['wei'] * from_wei(tranche['chk_vol'], 'ether'), 'ether')
    print(tabulate([
        ['VDOC limit', num_disp(from_wei(tranche['chk_lim'], 'ether'))],
        ['VDOC volume', num_disp(from_wei(tranche['chk_vol'], 'ether'))],
        ['ETH price / VDOC', num_disp(from_wei(tranche['wei'], 'ether'))],
        ['ETH total', num_disp(eth_total)],
        ['ETH TX limit', num_disp(eth_total / tranche_min_tx)],
    ]))
