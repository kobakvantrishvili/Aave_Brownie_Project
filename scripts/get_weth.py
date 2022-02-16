from scripts.helpful_scripts import get_account
from brownie import interface, network, config
from web3 import Web3


def main():
    get_weth()


def get_weth():
    """
    Mints WETH by depositing ETH.
    """
    # to interact with WETH contract we need:
    # ABI (got from interface)
    # Address (in yaml file)
    Account = get_account()
    weth = interface.IWeth(config["networks"][network.show_active()]["weth_token"])
    tx = weth.deposit({"from": Account, "value": Web3.toWei("0.1", "ether")}).wait(1)
    print("recieved 0.1WETH!")
    return tx
