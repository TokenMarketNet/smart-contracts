"""Tools for moving funds from a presale contract to ICO contract early."""
import logging

from web3 import Web3

from ico.utils import check_succesful_tx


logger = logging.getLogger(__name__)


def participate_early(chain, web3: Web3, presale_address: str, crowdsale_address: str, deploy_address: str) -> int:
    """Move funds over early.

    .. note ::

        Crowdsale contract checks the participate whitelist by invest address, not by msg.sender.
        This process will open the presale investors an ability to participate to the crowdsale early,
        bypassing the retail investor start time. However they could also top up their existing
        preico accounts, so this is largerly no issue.
    """

    updated = 0

    PresaleFundCollector = chain.contract_factories.PresaleFundCollector
    presale = PresaleFundCollector(address=presale_address)

    Crowdsale = chain.contract_factories.Crowdsale
    crowdsale = Crowdsale(address=crowdsale_address)

    # Make sure presale is correctly set
    txid = presale.transact({"from": deploy_address}).setCrowdsale(crowdsale.address)
    logger.info("Setting presale crowdsale address to %s on txid", crowdsale.address, txid)
    check_succesful_tx(web3, txid)

    # Double check presale has a presale price set
    MilestonePricing = chain.contract_factories.MilestonePricing
    pricing_strategy = MilestonePricing(address=crowdsale.call().pricingStrategy())

    if not pricing_strategy.call().preicoAddresses(presale.address):
        raise RuntimeError("Was not listed as presale address for pricing: {}".format(presale.address))

    for i in range(0, presale.call().investorCount()):

        investor = presale.call().investors(i)

        if presale.call().balances(investor) > 0:
            logger.info("Whitelisting for %s to crowdsale %s", investor, crowdsale.address)
            txid = crowdsale.transact({"from": deploy_address}).setEarlyParicipantWhitelist(investor, True)
            logger.info("Broadcasting whitelist transaction %s", txid)

            logger.info("Moving funds for %s to presale %s", investor, presale.address)
            txid = presale.transact({"from": deploy_address}).parcipateCrowdsaleInvestor(investor)
            logger.info("Broadcasting transaction %s", txid)
            check_succesful_tx(web3, txid)
            updated += 1

    return updated

