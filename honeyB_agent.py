import subprocess
import thread
import socket
import json
import time
import os
import base64
from datetime import datetime , date , time , timedelta

from scapy .all import *

 # color honey yellow is # a98307
port = 9830
transferPort = 9831
honeyHiveIP = ' 192.168.1.233 '
honeydIP = ' 192.168.1.154 '
honeypots = [" 192.168.1.150 ", " 192.168.1.151 ", " 192.168.1.152 "]
connections = {}
timeOutSeconds = 9000
sessionTimeout = timedelta ( seconds = timeOutSeconds )
autoTransferTimeout = timedelta ( seconds = timeOutSeconds )
connections_Lock = thread . allocate_lock ()
honeyd = None
devnull = open (os. devnull , 'wb ')
alertMode = False

def main ():
    global honeyd
    pcap_monitor_id = thread . start_new_thread ( pcapMonitor , ())
    # heartbeat_id = thread . start_new_thread ( heartbeat , ())

    # I want this in my main console output
    # once run , it casues blocking
    print " Scapy Packet Sniffer Engaged "
    sniff ( iface =" eth0 ", prn= processPacket , store =0)

def pcapMonitor ():
    while True :
        connections_Lock . acquire ()
        uct = datetime . utcnow ()
        remove = []
        for ip in connections :
            if (uct - connections [ip ]. get (" time ") >= autoTransferTimeout ):
                transferFile (ip , connections [ip ]. get ('filename '))
                remove.append (ip)
                print " Automatic Transfer "
    for i in remove :
        connections . pop(i)
    connections_Lock . release ()
    floatSeconds = timeOutSeconds *1.0
    time . sleep ( floatSeconds )

# method called when a packet is received
# parses the packet to identify the dest ip , port , ect.
# will implement scan recognition and attacker pivoting
def processPacket ( packet ):
    # automatically named files based on ip , date , and time
    now = datetime .now ()
    uct = datetime . utcnow ()