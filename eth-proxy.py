#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
import os
import sys
import socket

from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('proxy')

if __name__ == '__main__':
    if len(settings.WALLET)!=42 and len(settings.WALLET)!=40:
        log.error("Wrong WALLET!")
        sys.exit()
    settings.CUSTOM_EMAIL = settings.MONITORING_EMAIL if settings.MONITORING_EMAIL and settings.MONITORING else ""

from twisted.internet import reactor, defer, protocol
from twisted.internet import reactor as reactor2
from stratum.socket_transport import SocketTransportFactory, SocketTransportClientFactory
from stratum.services import ServiceEventHandler
from twisted.web.server import Site
from stratum.custom_exceptions import TransportException

from mining_libs import getwork_listener
from mining_libs import client_service
from mining_libs import jobs
from mining_libs import version

def on_shutdown(f):
    '''Clean environment properly'''
    log.info("Shutting down proxy...")
    if os.path.isfile('eth-proxy.pid'):
        os.remove('eth-proxy.pid')
    f.is_reconnecting = False # Don't let stratum factory to reconnect again

# Support main connection
@defer.inlineCallbacks
def ping(f):
    if not f.is_reconnecting:
        return
    try:
        yield (f.rpc('eth_getWork', [], ''))
        if f.is_failover:
            reactor.callLater(30, ping, f)
        else:
            reactor.callLater(5, ping, f)
    except Exception:
        pass

@defer.inlineCallbacks
def on_connect(f):
    '''Callback when proxy get connected to the pool'''
    log.info("Connected to Stratum pool at %s:%d" % f.main_host)
    f.is_connected = True
    f.remote_ip = f.client._get_ip()
    #reactor.callLater(30, f.client.transport.loseConnection)

    # Hook to on_connect again
    f.on_connect.addCallback(on_connect)

    # Get first job and user_id
    debug = "_debug" if settings.DEBUG else ""
    initial_job = (yield f.rpc('eth_submitLogin', [settings.WALLET, settings.CUSTOM_EMAIL], 'Proxy_'+version.VERSION+debug))

    reactor.callLater(0, ping, f)

    defer.returnValue(f)

def on_disconnect(f):
    '''Callback when proxy get disconnected from the pool'''
    log.info("Disconnected from Stratum pool at %s:%d" % f.main_host)
    f.is_connected = False
    f.on_disconnect.addCallback(on_disconnect)

@defer.inlineCallbacks
def main():
    reactor.disconnectAll()

    log.warning("Ethereum Stratum proxy version: %s" % version.VERSION)

    # Connect to Stratum pool, main monitoring connection
    log.warning("Trying to connect to Stratum pool at %s:%d" % (settings.POOL_HOST, settings.POOL_PORT))
    f = SocketTransportClientFactory(settings.POOL_HOST, settings.POOL_PORT,
                debug=settings.DEBUG, proxy=None,
                event_handler=client_service.ClientMiningService)

    f1 = None
    f2 = None
    f3 = None
    if settings.POOL_FAILOVER_ENABLE:
        log.warning("Trying to connect to failover Stratum pool-1 at %s:%d" % (settings.POOL_HOST_FAILOVER1, settings.POOL_PORT_FAILOVER1))
        f1 = SocketTransportClientFactory(settings.POOL_HOST_FAILOVER1, settings.POOL_PORT_FAILOVER1,
                debug=settings.DEBUG, proxy=None,
                event_handler=client_service.ClientMiningService)
        f1.is_failover = True

        log.warning("Trying to connect to failover Stratum pool-2 at %s:%d" % (settings.POOL_HOST_FAILOVER2, settings.POOL_PORT_FAILOVER2))
        f2 = SocketTransportClientFactory(settings.POOL_HOST_FAILOVER2, settings.POOL_PORT_FAILOVER2,
                debug=settings.DEBUG, proxy=None,
                event_handler=client_service.ClientMiningService)
        f2.is_failover = True

        log.warning("Trying to connect to failover Stratum pool-3 at %s:%d" % (settings.POOL_HOST_FAILOVER3, settings.POOL_PORT_FAILOVER3))
        f3 = SocketTransportClientFactory(settings.POOL_HOST_FAILOVER3, settings.POOL_PORT_FAILOVER3,
                debug=settings.DEBUG, proxy=None,
                event_handler=client_service.ClientMiningService)
        f3.is_failover = True

    job_registry = jobs.JobRegistry(f,f1,f2,f3)
    client_service.ClientMiningService.job_registry = job_registry
    client_service.ClientMiningService.reset_timeout()

    f.on_connect.addCallback(on_connect)
    f.on_disconnect.addCallback(on_disconnect)
    # Cleanup properly on shutdown
    reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f)
    if f1:
        f1.on_connect.addCallback(on_connect)
        f1.on_disconnect.addCallback(on_disconnect)
        reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f1)

    if f2:
        f2.on_connect.addCallback(on_connect)
        f2.on_disconnect.addCallback(on_disconnect)
        reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f2)

    if f3:
        f3.on_connect.addCallback(on_connect)
        f3.on_disconnect.addCallback(on_disconnect)
        reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f3)


    # Block until proxy connect to the pool
    try:
        yield f.on_connect
    except TransportException:
        log.warning("First pool server must be online first time during start")
        return


    conn = reactor.listenTCP(settings.PORT, Site(getwork_listener.Root(job_registry, settings.ENABLE_WORKER_ID)), interface=settings.HOST)

    try:
        conn.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # Enable keepalive packets
        conn.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 60) # Seconds before sending keepalive probes
        conn.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1) # Interval in seconds between keepalive probes
        conn.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 5) # Failed keepalive probles before declaring other end dead
    except:
        pass # Some socket features are not available on all platforms (you can guess which one)

    log.warning("-----------------------------------------------------------------------")
    if settings.HOST == '0.0.0.0':
        log.warning("PROXY IS LISTENING ON ALL IPs ON PORT %d" % settings.PORT)
    else:
        log.warning("LISTENING FOR MINERS ON http://%s:%d" % (settings.HOST, settings.PORT))
    log.warning("-----------------------------------------------------------------------")
    log.warning("Wallet: %s" % settings.WALLET)
    log.warning("Worker ID enabled: %s" % settings.ENABLE_WORKER_ID)
    if settings.MONITORING:
        log.warning("Email monitoring on %s" % settings.MONITORING_EMAIL)
    else:
        log.warning("Email monitoring disabled")
    log.warning("Failover enabled: %s" % settings.POOL_FAILOVER_ENABLE)
    log.warning("-----------------------------------------------------------------------")

if __name__ == '__main__':
    fp = file("eth-proxy.pid", 'w')
    fp.write(str(os.getpid()))
    fp.close()
    main()
    reactor.run()
