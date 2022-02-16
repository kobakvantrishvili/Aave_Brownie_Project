from scripts.helpful_scripts import get_account
from scripts.get_weth import get_weth
from brownie import network, config, interface
from web3 import Web3

amount = Web3.toWei("0.1", "ether")


def main():
    Account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in ["mainnet-fork", "kovan"]:
        get_weth()
    # Two things we need when working wih contract:
    # ABI
    # Address
    lending_pool = get_lending_pool()
    # aave has a seperate contract which is used to get the addresses of main aave contracts
    print(lending_pool)
    # we need to approve weth (ERC20 version of eth) token before we deposit it
    # approve function makes sure that when our token is used we granted the persmission
    approve_erc20(lending_pool.address, amount, erc20_address, Account)
    print("Depositing...")
    lending_pool.deposit(
        erc20_address, amount, Account.address, 0, {"from": Account}
    ).wait(1)
    print("Deposited!")
    # so how much can we borrow?
    (borrowable_eth, total_debt) = get_borrowable_data(lending_pool, Account)
    print("Let's borrow!")
    # In order to borrow we need price feed
    # DAI in terms of ETH
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )
    dai_eth_real_price = Web3.fromWei(dai_eth_price, "ether")
    print(f"The DAI/ETH price is {Web3.fromWei(dai_eth_price, 'ether')}")

    # borrowable_eth -> borrowable_dai * 95%
    amount_dai_to_borrow = float(1 / dai_eth_real_price) * (borrowable_eth * 0.95)
    # we multiply b 0.95 so that health factor is "better" and not get liquidated
    print(f"We are going to borrow {amount_dai_to_borrow} DAI")

    # Now we will borrw!
    dai_address = config["networks"][network.show_active()]["dai_token"]
    # borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)
    borrow_tx = lending_pool.borrow(
        dai_address,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        Account.address,
        {"from": Account},
    )
    borrow_tx.wait(1)
    print("We borrowed some DAI!")
    get_borrowable_data(lending_pool, Account)
    # now let's repay
    repay_all(amount, lending_pool, Account)
    print("You just deposited, borrowed and repayed with Aave, Brownie and Chainlink!")


def get_lending_pool():
    lending_pool_adresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_adresses_provider.getLendingPool()
    # Address - Done!
    # now we need to get the ABI
    # so we added ILendingPool.sol from aave docs, we had to add dependancies in .yaml because new .sol file imports other contracts, finally we compiled
    lending_pool = interface.ILendingPool(lending_pool_address)
    # lending_pool is lending pool contract that we can interact with
    return lending_pool


def approve_erc20(spender, amount, erc20_address, Account):
    # again to call approve function we need the token contract's:
    # ABI
    # Address
    print("Approving ERC20 token...")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": Account})
    tx.wait(1)
    print("Approved!")
    return tx


def get_borrowable_data(lending_pool, Account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrow_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(Account.address)

    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    print(f"You have {total_collateral_eth} worth of ETH deposited.")
    print(f"You have {total_debt_eth} worth of ETH borrowed.")
    print(f"You can borrow {available_borrow_eth} worth of ETH.")
    return (float(available_borrow_eth), float(total_debt_eth))


# get the price of some token in terms of eth
def get_asset_price(price_feed_address):
    # AGAIN grab:
    # ABI
    # ADDRESS
    tkn_eth_price_feed = interface.AggregatorV3Interface(price_feed_address)
    latest_price = tkn_eth_price_feed.latestRoundData()[1]
    # we returned first index cuz price is at that index, in general this returns tuple
    return latest_price


def repay_all(amount, lending_pool, Account):
    approve_erc20(
        lending_pool,
        Web3.toWei(amount, "ether"),
        config["networks"][network.show_active()]["dai_token"],
        Account,
    )
    # repay(address asset, uint256 amount, uint256 rateMode, address onBehalfOf)
    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["dai_token"],
        amount,
        1,
        Account.address,
        {"from": Account},
    )
    repay_tx.wait(1)
    print("Repayed!")
