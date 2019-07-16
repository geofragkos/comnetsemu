#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
"""

import comnetsemu.tool as tool
from time import sleep
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 3


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addDockerHost('h1', dimage='sec_test', ip='10.0.0.1',
                           cpuset_cpus="1", cpu_quota=25000)
    h2 = net.addDockerHost('h2', dimage='nginx', ip='10.0.0.2',
                           cpuset_cpus="1", cpu_quota=25000)
    h3 = net.addDockerHost('h3', dimage='sec_test', ip='10.0.0.3',
                           cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h3, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    # TODO: IP is not assigned by mininet for some reason
    h2.cmd("ip a a 10.0.0.2/24 dev h2-s1")

    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    info('\n')

    # Create blacklist
    info('*** Create blacklist\n')
    h2.cmd("nft add table inet filter")
    h2.cmd("nft add chain inet filter input { type filter hook input priority 0 \; policy accept \; }")
    h2.cmd("nft add rule inet filter input ip saddr 10.0.0.3 drop")

    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    # Eve changes her ip address
    info("*** Eve changes ip address\n")
    h3.cmd("ip a f dev h3-s1")
    h3.cmd("ip a a 10.0.0.10/24 dev h3-s1")

    # Eva can connect again
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    info('\n')

    # Change to whitelist
    info('*** Create whitelist\n')
    h2.cmd("nft flush rule inet filter input")
    h2.cmd("nft add rule inet filter input ip saddr 10.0.0.1 accept")
    h2.cmd("nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }")

    # The server can talk back to Bob
    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")
    # But he cannot talk to some other server on the internet, this is a problem
    info('** h2 -> internet\n')
    test_connection(h2, "8.8.8.8")

    info('\n')

    # Lets enable some connection tracking
    info('*** Enable connection tracking\n')
    h2.cmd("nft add rule inet filter input ct state established,related accept")

    info('** h2 -> internet\n')
    test_connection(h2, "8.8.8.8")

    info('\n')

    info('*** Stopping network')
    net.stop()


def test_connection(source_container, target_ip):
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    if measured == 0.0:
        info('* Connection established\n')
    else:
        info('* Connection denied\n')


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
