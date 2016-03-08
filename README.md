#Description

This is Stratum Proxy for Ethereum based pools (RPCv2) using asynchronous networking written in Python Twisted.
Originally developed for DwarfPool http://dwarfpool.com/eth

**NOTE:** This fork is still in development. Some features may be broken. Please report any broken features or issues.


#Features

* Additional up to 20% increase of earning compared to standard pools
* ETH stratum proxy
* Automatically failover via proxy
* Only one connection to the pool
* Workers get new jobs immediately
* Submit of shares without network delay, it's like solo-mining but with benefits of professional pool
* Central Wallet configuration, miners doesn't need wallet as username
* Support monitoring via email
* Bypass worker_id for detailed statistic and per rig monitoring
* pass submitHashrate to pool

#How it works

   Pool A <---+                        +-------------+ Rig1 / PC1
 (Active)      |                       |
               |                       +-------------+ Rig2 / PC2
               |                       |
  Pool B <---+-----StratumProxy  <-----+-------------+ Rig3 / PC3
(FailOver)                             |
                                       +-------------+ Rig4 / PC4
                                       |
                                       +-------------+ Leaserigs


#ToDo

* ---


#Configuration

* all configs in file  eth-proxy.conf


#Command line to miner start, recommended farm-recheck to use with stratum-proxy is 200

* ./ethminer --farm-recheck 200 -G -F http://127.0.0.1:8080/rig1


#External script to restart proxy (made by rain)

* https://paste.ubuntu.com/15327007/


# Proxy working check

* To check that proxy works open in browser http://127.0.0.1:8080/ (or your changed ip and port from config)
* If you see "Ethereum stratum proxy" and some infos about connections.
* If not then mostly case that you have application running on this port, at example Antivirus.


#Donations

* ETH:  0xea7263feb7d8a8ab0a11eedd8f1ce04412ab0820


#Requirements

eth-proxy is built in python. I have been testing it with 2.7.3, but it should work with other versions. The requirements for running the software are below.

* Python 2.7+
* python-twisted


#Installation and start

* [Linux]
1) install twisted
 apt-get install python-twisted
2) start proxy with
 python ./eth-proxy.py

* [Windows]
Download compiled version
https://github.com/Atrides/eth-proxy/releases

Or use python source code

1) Download Python Version 2.7.10 for Windows
https://www.python.org/downloads/

2) Modify PATH variable (how-to http://www.java.com/en/download/help/path.xml) and add
   C:\Python27;C:\Python27\Scripts;

3) Install python setuptools
https://pypi.python.org/pypi/setuptools/#windows-7-or-graphical-install

4) Install Python-Twisted
https://pypi.python.org/pypi/Twisted/15.4.0
File Twisted-15.4.0.win32-py2.7.msi (32bit) or Twisted-15.4.0.win-amd64-py2.7.msi (64bit)

5) Install zope.interface, in console run:
   easy_install -U zope.interface

6) Install PyWin32 v2.7
pywin32-219.win32-py2.7.exe or pywin32-219.win-amd64-py2.7.exe
http://sourceforge.net/projects/pywin32/files/pywin32/

7) Download eth-proxy. Extract eth-proxy.zip. Change settings in config.py and start with command:
  python xmr-proxy.py


#Contact

* I am available via admin@dwarfpool.com

#Credits

* Original version by Slush0 (original stratum code)
* More Features added by GeneralFault, Wadee Womersley and Moopless

#License

* This software is provides AS-IS without any warranties of any kind. Please use at your own risk.
