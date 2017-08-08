"""Tools for moving funds from a presale contract to ICO contract early."""
import logging

from eth_utils import from_wei
from web3 import Web3

from ico.utils import check_succesful_tx
from ico.utils import get_contract_by_name


logger = logging.getLogger(__name__)


def participate_early(chain, web3: Web3, presale_address: str, crowdsale_address: str, deploy_address: str, start=0, end=32, timeout=300) -> int:
    """Move funds over early.

    .. note ::

        Crowdsale contract checks the participate whitelist by invest address, not by msg.sender.
        This process will open the presale investors an ability to participate to the crowdsale early,
        bypassing the retail investor start time. However they could also top up their existing
        preico accounts, so this is largerly no issue.


    :param start: Move only n investors (for testing purposes)
    :param end: Move only n investors (for testing purposes)
    """

    updated = 0

    PresaleFundCollector = get_contract_by_name(chain, "PresaleFundCollector")
    presale = PresaleFundCollector(address=presale_address)

    Crowdsale = PresaleFundCollector = get_contract_by_name(chain, "Crowdsale")
    crowdsale = Crowdsale(address=crowdsale_address)

    # Make sure presale is correctly set
    txid = presale.transact({"from": deploy_address}).setCrowdsale(crowdsale.address)
    logger.info("Setting presale crowdsale address to %s on txid", crowdsale.address, txid)
    check_succesful_tx(web3, txid, timeout=timeout)

    # Double check presale has a presale price set
    MilestonePricing = get_contract_by_name(chain, "MilestonePricing")
    pricing_strategy = MilestonePricing(address=crowdsale.call().pricingStrategy())

    if not pricing_strategy.call().preicoAddresses(presale.address):
        raise RuntimeError("Was not listed as presale address for pricing: {}".format(presale.address))

    for i in range(start, min(end, presale.call().investorCount())):

        investor = presale.call().investors(i)

        if presale.call().balances(investor) > 0:
            print("Whitelisting for {} to crowdsale {}".format(investor, crowdsale.address))
            txid = crowdsale.transact({"from": deploy_address}).setEarlyParicipantWhitelist(investor, True)
            print("Broadcasting whitelist transaction {}".format(txid))
            check_succesful_tx(web3, txid, timeout=timeout)

            funds = from_wei(presale.call().balances(investor), "ether")
            print("Moving funds {} ETH for investor {} to presale {}".format(funds, investor, presale.address))
            txid = presale.transact({"from": deploy_address}).parcipateCrowdsaleInvestor(investor)
            print("Broadcasting transaction {}".format(txid))
            check_succesful_tx(web3, txid, timeout=timeout)
            updated += 1
        else:
            print("Investor already handled: {}".format(investor))

    return updated

