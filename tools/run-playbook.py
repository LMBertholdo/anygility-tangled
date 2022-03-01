#!/usr/bin/env python3
# coding: utf-8
###############################################################################
# run-playbook - Apply a playbook routing instructions contained on a file or
#               using command line arguments.
#
# Copyright (C) 2022 by University of Twente
# Written by Joao Ceron <ceron@botlog.org> and  
#            Leandro Bertholdo <leandro.bertholdo@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
###############################################################################
version = 0.21
verbose = True

###############################################################################
### Python modules
import pandas as pd
from pandas.io.parsers import ParserError
import sys
import paramiko
import re
import argparse
from argparse import RawTextHelpFormatter
import logging
import sys
import os
from os import linesep
import importlib as imp
import signal
import cursor
import numpy as np

###############################################################################
### Program settings
program_name = sys.argv[0][:-3]

### TESTBED NODES
nodes = {
          "au-syd-anycast01" : "108.61.185.44",
          "br-gru-anycast01" : "200.136.41.30",
          "br-poa-anycast02" : "177.184.254.162",
          "dk-cop-anycast01" : "193.163.102.207",
          "fr-par-anycast01" : "45.32.151.68",
#          "jp-hnd-anycast01" : "203.178.148.30",
          "nl-arn-anycast01" : "193.176.144.173",
          "nl-ams-anycast01" : "136.244.104.73",
          "nl-ens-anycast02" : "192.87.172.193",
          "uk-lnd-anycast02" : "108.61.172.212",
          "us-mia-anycast01" : "198.32.252.97",
          "us-was-anycast01" : "128.9.63.135",
          "us-los-anycast01" : "128.9.29.4",
          "de-fra-anycast01" : "95.179.245.34",
          "us-sea-anycast01" : "137.220.39.22",
          "sg-sin-anycast01" : "139.180.131.134",
          "za-jnb-anycast01" : "196.251.250.248",
#          "br-gig-anycast01" : "152.84.200.22",
}

###############################################################################
### Subrotines

#------------------------------------------------------------------------------
def set_log_level(log_level=logging.INFO):
    """Sets the log level of the notebook. Per default this is 'INFO' but
    can be changed.
    :param level: level to be passed to logging (defaults to 'INFO')
    :type level: str
    """
    imp.reload(logging)
    logging.basicConfig(
            level=log_level,
            format='%(asctime)s.%(msecs)03d %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
    )

#------------------------------------------------------------------------------
def parser_args ():

    #parser = argparse.ArgumentParser(prog=program_name, usage='%(prog)s [options]', formatter_class=RawTextHelpFormatter)
    parser = argparse.ArgumentParser(prog=program_name, usage='%(prog)s [options]')
    parser.add_argument("--version", help="print version and exit", action="store_true")
    parser.add_argument("-d","--debug", help="print debug messages", action="store_true")
    parser.add_argument("-v", help="print verbose messages", action="store_true",dest="verbose")
    parser.add_argument("-s","--show", help="show active announces", action="store_true")
    #parser.add_argument("-r","--rm", help="remove all routes on testbed", action="store_true")
    parser.add_argument("-t","--test", help="test if a playbook file is consistent", action="store_true")
    parser.add_argument('--playbook', nargs='?', help="apply routing file playbook",dest="playbook")
    parser.add_argument('--key', nargs='?', help="SSH key present on the testbed",dest="key",default= "~/.ssh/id_ed25519")
    parser.add_argument('--user', nargs='?', help="SSH user used to login on the testbed",dest="user", default="testbed")
    return parser

#------------------------------------------------------------------------------
# check parameters
def evaluate_args():
    parser = parser_args()
    args = parser.parse_args()

    if (args.version):
        print (version)
        sys.exit(0)

    if (args.debug):
        set_log_level('DEBUG')
        logging.debug(args)

    if (args.verbose):
        set_log_level('INFO')
        logging.debug(args)

    if (args.playbook or args.test):
        if check_playbook_file(args.playbook):
            if not args.test:
                run_playbook(args.playbook,args.user,args.key)
                show_all_active_routes(args.user,args.key)
            else:
                print("Playbook is OK")
        else:
            print("Playbook contains errors")

    if (args.show):
        print (f"Showing active routes on Anycast Network [{len(nodes)}] sites")
        show_all_active_routes(args.user,args.key)

    if (args.playbook==None) and (not args.show):
        parser.print_help()
        
    return (args)

#------------------------------------------------------------------------------
def signal_handler(sig, frame):
    print('Ctrl+C detected.')
    cursor.show()
    sys.exit(0)

#------------------------------------------------------------------------------
def connect(node,user,key):
    """ create the handler to connect to the SSH sections
        :param: 
                node - string that is mapped to an IP address
    """

    #user  = args.user
    #key = args.key
    #if not args.key in globals():
    #    logging.debug('running function mode')
    #    key="~/.ssh/id_ed25519"
    #if not args.user in globals():
    #    logging.debug('running function mode')
    #    user='testbed'
    ip = nodes.get(node)
    if not ip:
        print ("node: {}, not found!".format(node))
        print ("check available nodes")
    
    logging.info("connect:: user[%s] ip[%s] key[%s]", user, ip, key)

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user)
    except paramiko.ssh_exception.NoValidConnectionsError as inst:
        print("username [{}] not exists".format(user))
    except paramiko.ssh_exception.AuthenticationException as inst:
        print("-->> Key or password are not correct ({},{},{},{})".format(node.upper(),ip,user.upper(),key))
        #print("-->> more info on except inst: [{}][{}][{}])".format(type(inst),inst,inst.args))
    except paramiko.ssh_exception.BadHostKeyException as inst:
        print("Unable to verify server's host key: {}".format(inst))
    except Exception as inst:
        print ("Could not connect in node {}".format(node.upper()))
        print ("Ignoring node {}".format(node.upper()))
        print("SSH exception:",type(inst),inst)
        return (None)

    return (ssh)

#------------------------------------------------------------------------------
def run_cmd(node, user, key, cmd):
    """ Run a cmd using the established SSH session
        param node: name (string) that represent the node (see dic)
        return: array of lines
    """
    logging.debug("run_cmd::going to connect [%s]", node)
    ssh = connect(node,user,key)
    logging.debug("run_cmd::after connect")
    if (not ssh):
        return (None)

    shell = ssh.invoke_shell()
    logging.debug("run_cmd::after invoke_shell")

    shell.settimeout(3)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.readlines()
    err = stderr.readlines()

    # Clean up elements - for some reason, garbage is not cleared at close() so need delete elements
    ssh.close()
    del ssh, stdin, stdout, stderr
    
    #if (len(err)):
    #    print(f"==>Error setting node[{node}] cmd[{cmd}] ")
    #    print(f"==>[{err}]")
    #    return(None)

    return(out)

#------------------------------------------------------------------------------
def check_playbook_file (playbook):
    logging.info("check_playbook")
    min_info=['site', 'prefix']

    try :
        df=pd.read_csv(playbook,comment='#')
    except ParserError:
        print(f"Playbook file is out of format [{playbook}]")  
        raise
    except FileNotFoundError:
        print(f"Playbook file not found at [{playbook}]")
        raise
    else:
        cols=list(df.columns)
        if len(list(set(cols).intersection(min_info)))<2:
            print (f"Not found minimum elements on Playbook {min_info}")
        else: 
            return (True)
    
    return (False)

#------------------------------------------------------------------------------
def run_playbook (playbook,user,key):
    logging.info("Running Playbook")
    df=pd.read_csv(playbook,comment='#')
    df=df.fillna('')

    #print ('Configuring: ', end='')

    for index, row in df.iterrows():
        logging.info(f"ROW: {row.to_dict()}")

        # look what columns this playbook entry have
        col_names=row.index
        node=row['site']
        prefix=row['prefix']

        #print (f' {node}', end='')#

        # Check if routing file have some fields
        if ('peer_as' in col_names) and len(str(row['peer_as'])):
            peer_as=row['peer_as']
        else: 
            peer_as=None

        if ('neighbor' in col_names) and len(row['neighbor']):
            nei=row['neighbor']
        else: 
            nei=None

        if ('attributes' in col_names) and len(row['attributes']):
            attr=row['attributes']
        else:
            attr=None

        logging.info(f'=== node [{node}]  nei[{nei}]  prefix [{prefix}]  attr [{attr}]===')

        # Decide what to run on testbed node
        if ( (node is not None) and (nei is not None) and (prefix is not None) and (attr is not None) ):
            # bgp community
            if 'community' in attr:
                logging.info('==> bgp community found')                
                attr=attr.replace('community','')
                cmd = f"exabgpcli neighbor {nei} announce route {prefix}  next-hop self extended-community {attr}"
                logging.info(cmd)
                logging.info (f"[{node}] Announcing {prefix} on neighbor {nei} comm {attr}") 
                output = run_cmd(node,user,key,cmd)

            # prepends and poisoning
            if 'as-path' in attr:
                logging.info('==> as-path found')
                cmd = f"exabgpcli neighbor {nei} announce route {prefix}  next-hop self {attr}"
                logging.info(cmd)
                logging.info (f"[{node}] Announcing {prefix} on neighbor {nei} {attr}") 
                output = run_cmd(node,user,key,cmd)

        elif ( (node is not None) and (nei is not None) and (prefix is not None) ):
            cmd=f"exabgpcli neighbor {nei} announce route {prefix}  next-hop self"
            logging.info(cmd)
            logging.info (f"[{node}] Announcing {prefix} on neighbor {nei}") 
            output = run_cmd(node,user,key,cmd)
            
        elif ((node is not None) and (prefix is not None)):  
            # advertise on all neighbors 
            logging.info(f"finding neighbor for {node}")
            logging.info (f" Announcing {prefix} to All Peers on {node}")

            # need to discover active neighbors
            cmd = "exabgpcli show neighbor summary"

            output = run_cmd(node,user,key,cmd)
            logging.info (f'output ==> {output}')
            output = parse_peers(output)
            logging.info (f'output ==> {output}')

            neighbor_list = [neighbor['ip'] for neighbor in output if ':' not in neighbor['ip']]
            logging.info (f"neighbor_list ==> {neighbor_list}")

            print (f'Peers {neighbor_list}')
            logging.info(f"Neighbors discovered: {neighbor_list}")

            # Announce to all node peers
            for nei in neighbor_list:
                cmd=f"exabgpcli neighbor {nei} announce route {prefix} next-hop self"
                logging.info(cmd)
                logging.info (f"[{node}] Announcing {prefix} on neighbor {nei}") 
                output = run_cmd(node,user,key,cmd)
                if (output):
                    print (output)

        else:
            print ('Could not exec Playbook...')

    #print ('\n')
        
    


#------------------------------------------------------------------------------
def show_active_routes_on_node(node,user,key):
    cmd = "exabgpcli show adj-rib out extensive"
    output = run_cmd(node,user,key,cmd)
    if (not output):
        return False;
    else:
        #print ("== {}".format(node))
        for line in (output):
            if (" in-open ipv4" in line):
                route_search = re.search('neighbor\s+(.*)\s+local-ip+.*in-open ipv\d\sunicast\s+(.*?)\s+next-hop self\s+(.*)',line,re.IGNORECASE)
                print ("[{}] neighbor {} prefix {} {} ".format(node, route_search.group(1),route_search.group(2),route_search.group(3)))
            else:
                print(line)    
        return True

#------------------------------------------------------------------------------
def show_all_active_routes(user,key):
    print ('Configuring routes...')
    active_nodes=0
    for node in nodes:
        if show_active_routes_on_node(node,user,key):
            active_nodes=active_nodes+1
    if active_nodes:
        print (f" Configured [{active_nodes}] nodes ") 
    else:
        print(f"Currently zero prefixes announced")



#------------------------------------------------------------------------------
def parse_peers(output):
    """ Parse the output from the command show neighbor summary
        param: output
        return: dictionary of peer and respective status
    """ 
    peer = []
    status = []
    logging.debug('Parsing peers for neighbor_list')
    # ignore first line
    output = output[1:]
    for line in (output):
        status = re.findall(r"established", line)
        if not status:
            status.append("\033[1mnot established\033[0m")
        result = {
            "ip": line.split()[0],
            "status" : status[0],
        }
        peer.append(result)

    return (peer)

# #------------------------------------------------------------------------------
# def remove_all_testbed_routes(user,key):
#     logging.info(f"Clearing testbed routing")
#     for node in list(nodes.keys()):
#         cmd = "exabgpcli show adj-rib out extensive"
#         output = run_cmd(node,user,key,cmd)
#         
#         # empty table
#         if (not output):
#             logging.info(f"[{node}] No adj-rib out ")
#             continue;
#             
#         #got something - go to parse
#         output = parse_withdraw_routes(output)
#         logging.info("parsed --> %s",output)   
#         
#         # No route found
#         if not output:
#             logging.info(f"[{node}] No routes")
#             continue;
#             
#         else:
#             # route found - remove
#             for announces in output:
#                 cmd = "exabgpcli neighbor {} {} ".format(announces['ip'],announces['cmd'])
#                 logging.info(f"withdraw: {output}")
#                 output = run_cmd(node,cmd)
#                 logging.debug(output)
#                 print (f"{cmd} withdraw... done!")
#     return None
#     
# #------------------------------------------------------------------------------
# def parse_withdraw_routes(output):
#     """ Parse the output from the command show neighbor adj-out
#         param: output
#         return: dictionary of peer and respective status
#     """
#     peer = []
#     status = []
#     result = []
#     for line in (output):
#         route_search = re.search('neighbor\s+(.*)\s+local-ip+.*in-open ipv\d\sunicast\s+(.*?)\s+next-hop self\s+(.*)',line,re.IGNORECASE)
#         #route_search = re.search('neighbor\s+(.*)\s+local-ip+.*in-open ipv\d\sunicast\s+(.*)', line, re.IGNORECASE)
# 
#         if ( not args.route or args.route == route_search.group(2)):
#             result = {
#                 "ip": route_search.group(1),
#                 "cmd" : "withdraw route "+route_search.group(2)
#                 }
#             peer.append(result)
# 
#         else:
#             logging.debug("Route [%s] for withdraw not found on peer [%s] route [%s]", args.route, route_search.group(1), route_search.group(2))
#     return (peer)

###############################################################################
### Main Process
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    args = evaluate_args()
    logging.debug(args)


