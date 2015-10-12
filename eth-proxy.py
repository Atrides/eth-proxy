#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
import os
import socket

from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('proxy')

if __name__ == '__main__':
    if len(settings.WALLET)!=42 and len(settings.WALLET)!=40:
        log.error("Wrong WALLET!")
        quit()
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
from mining_libs.jobs import Job

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
        reactor.callLater(60, ping, f)
    except Exception:
        pass

@defer.inlineCallbacks
def on_connect(f):
    '''Callback when proxy get connected to the pool'''
    log.info("Connected to Stratum pool at %s:%d" % f.main_host)
    #reactor.callLater(30, f.client.transport.loseConnection)
    
    # Hook to on_connect again
    f.on_connect.addCallback(on_connect)
    
    # Get first job and user_id
    initial_job = (yield f.rpc('eth_submitLogin', [settings.WALLET, settings.CUSTOM_EMAIL], 'Proxy_'+version.VERSION))

    reactor.callLater(0, ping, f)

    defer.returnValue(f)
     
def on_disconnect(f):
    '''Callback when proxy get disconnected from the pool'''
    log.info("Disconnected from Stratum pool at %s:%d" % f.main_host)
    f.on_disconnect.addCallback(on_disconnect)

    # Prepare to failover, currently works very bad
    #if f.main_host==(settings.POOL_HOST, settings.POOL_PORT):
    #    main()
    #else:
    #    f.is_reconnecting = False
    #return f

@defer.inlineCallbacks
def main():
    reactor.disconnectAll()
    failover = False
    if settings.POOL_FAILOVER_ENABLE:
        failover = settings.failover_pool
        settings.failover_pool = not settings.failover_pool

    pool_host = settings.POOL_HOST
    pool_port = settings.POOL_PORT
    if failover and settings.POOL_FAILOVER_ENABLE:
        pool_host = settings.POOL_HOST_FAILOVER
        pool_port = settings.POOL_PORT_FAILOVER

    log.warning("Ethereum Stratum proxy version: %s" % version.VERSION)
    log.warning("Trying to connect to Stratum pool at %s:%d" % (pool_host, pool_port))

    # Connect to Stratum pool, main monitoring connection
    f = SocketTransportClientFactory(pool_host, pool_port,
                debug=settings.DEBUG, proxy=None,
                event_handler=client_service.ClientMiningService)

    job_registry = jobs.JobRegistry(f)
    client_service.ClientMiningService.job_registry = job_registry
    client_service.ClientMiningService.reset_timeout()

    f.on_connect.addCallback(on_connect)
    f.on_disconnect.addCallback(on_disconnect)
    # Cleanup properly on shutdown
    reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f)

    # Block until proxy connect to the pool
    try:
        yield f.on_connect
    except TransportException:
        log.warning("First pool server must be online first time to start failover")
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
        log.warning("Email monitoring diasbled")
    #log.warning("Failover enabled: %" % settings.POOL_FAILOVER_ENABLE)
    log.warning("-----------------------------------------------------------------------")

if __name__ == '__main__':
    fp = file("eth-proxy.pid", 'w')
    fp.write(str(os.getpid()))
    fp.close()
    settings.failover_pool = False
    main()
    reactor.run()
