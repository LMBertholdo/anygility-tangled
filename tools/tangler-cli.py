#!/usr/bin/env python3
# coding: utf-8
###############################################################################
# Testbed CLI - interface for exabgpcli
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
# Apr Fri 24 21:51:33 BST 2019 - Initial version
# 24Apr20 v0.22 - Included br-gru-anycast01
# 23Sep20 v0.23 - changed poa and los
# 24Sep20 v0.24 - added de-fra, us-sea, sg-sin
# 10Oct20 v0.26 - added za-jnb br-gig
# 22Oct20 v0.30 - added -w[all|route]
# 28Nov20 v0.31 - garbage collection at paramiko (del ssh,stdin,stdout, stderr)
# 19Jan21 v0.32 - error exception bug on paramiko 
# 15Nov21 v0.33 - deactivated jp-hnd and br-gig
# 14Feb22 v0.34 - added peer/as info to csv output (multipeering site)
# 24Feb22 V0.35 - Improved error handling 
###############################################################################
version = 0.35
verbose = False
###############################################################################
### Python modules
import paramiko
import re
from argparse import RawTextHelpFormatter
import logging
import os
import sys
import argparse
from os import linesep
import importlib as imp
import signal
import cursor
import time
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
def connect(node):
    """ create the handler to connect to the SSH sections
        :param: 
                node - string that is mapped to an IP address
    """
    user  = args.user
    ip = nodes.get(node)
    if not ip:
        print ("node: {}, not found! DNS maybe?".format(node))
        print ("check available nodes")
        sys.exit(1)
    
    key = args.key
    logging.info(f"connect:: user[{user}] ip[{ip}] key[{key}]")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, timeout=10)

    except paramiko.ssh_exception.NoValidConnectionsError as inst:
        logging.exception(f"ERROR: username [{user}] do not exist!")
        sys.exit(1)    

    except paramiko.ssh_exception.AuthenticationException as inst:
        logging.exception(f"ERROR: Key or password are not correct {node.upper()},{ip},{user},{key}")
        sys.exit(1)

    except paramiko.ssh_exception.BadHostKeyException as inst:
        logging.exception(f"ERROR: Unable to verify server's host key: {inst}")
        sys.exit(1)

    except Exception as inst:
        logging.exception (f"ERROR: Could not connect in node {node.upper()}")
        logging.exception (f"ERROR: Ignoring node {node}")
        logging.exception (f"ERROR: SSH exception: {type(inst)},{inst}")
        return (None)
    return (ssh)

#------------------------------------------------------------------------------
def signal_handler(sig, frame):
    print('Ctrl+C detected.')
    cursor.show()
    sys.exit(0)

#------------------------------------------------------------------------------
def run_cmd(node,cmd):
    """ Run a cmd using the established SSH session
        param node: name (string) that represent the node (see dic)
        return: array of lines
    """
    logging.info(f"run_cmd:: [{node}] ==> [{cmd}]")
    ssh = connect(node)
    
    if (not ssh):
        logging.exception(f"run_cmd:: [{node}] SSH Failed]")
        logging.exception(f"run_cmd:: [{node}] Trying one more time after 15sec! ]")
        time.sleep(15)
        ssh = connect(node)
        if (not ssh):
            return (None)

    logging.info("run_cmd:: invoke_shell")
    shell = ssh.invoke_shell()
    

    shell.settimeout(0.0)
    stdin, stdout, stderr = ssh.exec_command(cmd)

    opt = stdout.readlines()
    opt1 = stderr.readlines()
    logging.info(f"run_cmd:: STDOUT[{opt}], STDERR[{opt1}]")

    #logging.info(f"run_cmd:: opt [{opt}]")

    # Clean up elements - for some reason, garbage is not cleared at close() so need delete elements
    ssh.close()
    del ssh, stdin, stdout, stderr

    return(opt)

#------------------------------------------------------------------------------
def parse_withdraw_routes(output):
    """ Parse the output from the command show neighbor adj-out
        param: output
        return: dictionary of peer and respective status
    """ 
    peer = []
    status = []
    result = []
    for line in (output):
        route_search = re.search('neighbor\s+(.*)\s+local-ip+.*in-open ipv\d\sunicast\s+(.*?)\s+next-hop self\s+(.*)',line,re.IGNORECASE)
        #route_search = re.search('neighbor\s+(.*)\s+local-ip+.*in-open ipv\d\sunicast\s+(.*)', line, re.IGNORECASE)

        if ( not args.route or args.route == route_search.group(2)):
            result = {
                "ip": route_search.group(1),
                "cmd" : "withdraw route "+route_search.group(2)
                }
            peer.append(result)

        else:
            logging.debug("Route [%s] for withdraw not found on peer [%s] route [%s]", args.route, route_search.group(1), route_search.group(2))
    return (peer)

#------------------------------------------------------------------------------
def parse_peers(output):
    """ Parse the output from the command show neighbor summary
        param: output
        return: dictionary of peer and respective status
    """ 
    peer = []
    status = []
    
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
    parser.add_argument("-4", help="working on IPv4 neighbor", action="store_true",dest="v4")
    parser.add_argument("-6", help="working on IPv6 neighbor", action="store_true",dest="v6")
    parser.add_argument("--status", help="status of neighbor", action="store_true")
    parser.add_argument("--csv", help="CSV output", action="store_true")
    parser.add_argument("-a","--announces", help="active announces", action="store_true")
    parser.add_argument('-t','--target', nargs='?', help="target [node|all]")
    parser.add_argument('-c','--cmd', nargs='?', help="cmd to be executed")
    parser.add_argument('-A', help="announce routes [-r] to a target [-t] or all nodes/routes (default) ",action="store_true",dest="add")
    parser.add_argument('-P', nargs='?', help="number of prepends",dest="prepend")
    parser.add_argument('-r', nargs='?', help="BGP route to be added",dest="route")
    parser.add_argument('--key', nargs='?', help="SSH key present on the testbed",dest="key", default= "~/.ssh/id_ed25519")
    parser.add_argument('--user', nargs='?', help="SSH user used to login on the testbed",dest="user", default="testbed")
    parser.add_argument("-w", help="withdraw routes [-r] from a target [-t] or all nodes/routes (default) ", action="store_true",dest="withdraw")
    parser.add_argument("--nodes-with-announces", help="list the name of nodes with active prefix announcement", action="store_true",dest="listnodesannounce")
    return parser

#------------------------------------------------------------------------------
# check parameters
def evaluate_args():
    parser = parser_args()
    args = parser.parse_args()

    # Default is just v4
    if (not args.v6):
        args.v4 = True

    if (args.debug):
        set_log_level('DEBUG')
        logging.debug(args)

    if (args.verbose):
        set_log_level('INFO')
        logging.debug(args)

    if (args.version):
        print (version)
        sys.exit(0)

    # you should provide the route to be add
    if (args.add and not args.route):
        print ("you should specify the route: ex. 145.100.118.0/23")
        parser.print_help()
        sys.exit(0)

    if (args.status or args.announces or args.withdraw or args.add or args.listnodesannounce):
        # for status assume target = all as default
        if (not args.target):
            args.target = "all" 

    # run cmd
    elif (not args.cmd):
        print ("you should enter the exabgp cmd to be executed in the exabgpcli")
        print ("neighbor 193.176.144.162 announce route 145.90.8.0/24 next-hop self community 100:667")
        parser.print_help()
        sys.exit(0)

    # check target node
    if (not args.target):
        parser.print_help()
        print ("you should enter the target [all|node]")
        print ("\t available nodes: {}".format(list(nodes.keys())))
        sys.exit(0)
    else:

        if (args.target == "all"):
            args.target = list(nodes.keys())
            logging.debug(args.target)
        else:
            for node in list(nodes.keys()):
                if (args.target==node):
                    args.target = node.split()
                    return (args)
            parser.print_help()
            print ("you should enter the target [node]")
            print ("\t available nodes: {}".format(list(nodes.keys())))
            sys.exit(0)
    return (args)

###############################################################################
### Main Process

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    available_nodes = list(nodes.keys())
    args = evaluate_args()
    logging.debug(args)

    logging.info("Started on [ %s ]", nodes)

    if (args.status):
        # check status
        logging.info(f"=== STATUS ===")
        for node in args.target:
            logging.info ("working on Status of [ %s ]", format(node))
            cmd = "exabgpcli show neighbor summary"
 
            logging.info("### Go Run cmd[%s]", cmd)
            _output = run_cmd(node,cmd)
            logging.info(f"Now parse output [{_output}]")
            if (not _output):
                logging.info(f"No neighbor summary output [{node}]")
                continue;
            output = parse_peers(_output)
            logging.info("parsed --> %s",output)

            for neighbor in output:
                #print ("\t{} - {} - {} ".format(node, neighbor['ip'], neighbor['status']))
                print ("{},{},{}".format(node, neighbor['ip'], neighbor['status']))
    
    elif (args.withdraw):
        logging.info(f"=== WITHDRAW ===")
        logging.info("withdraw [%s] from [%s]", args.route, args.target)
        for node in args.target:
            cmd = "exabgpcli show adj-rib out extensive"

            logging.info("### Go Run cmd[%s]", cmd)
            _output = run_cmd(node,cmd)
            logging.info(f"Now parse output [{_output}]")
            if (not _output):
                logging.info(f"No adj-rib out [{node}]")
                continue;
            output = parse_withdraw_routes(_output)
            logging.info("parsed --> %s",output)
           
            if not output:
                logging.info(f"there is nothing announced in {node} to withdraw")
            else:
                # announce found
                for announces in output:
                    cmd = "exabgpcli neighbor {} {} ".format(announces['ip'],announces['cmd'])
                    logging.info(f"withdraw: {output}")
                    if (args.v4):
                        if (':' not in announces['ip']):
                            output = run_cmd(node,cmd)
                            logging.debug(output)
                            print (f"{cmd} IPv4 withdraw... done!")

                    elif (args.v6):
                        if (':' in announces['ip']):
                            output = run_cmd(node,cmd)
                            logging.debug(output)
                            print (f"{cmd} IPv6 withdraw... done!")

                    # run for both
                    else:
                        output = run_cmd(node,cmd)
                        logging.debug(output)
                        print (f"{cmd} IPv4/6 withdraw... done!")
    
    # check all the announces for specific nodes
    elif (args.announces):
        logging.info(f"=== ANNOUNCES ===")
        if (args.csv):
            print ('site,prefix,peer_as,neighbor,attributes')
        for node in args.target:
            logging.info ("working on Announces of [ %s ]", format(node))
            cmd = " exabgpcli show adj-rib out extensive"
            output = run_cmd(node,cmd)
            if (not output):
                logging.info(f"[{node}] No announcement - no rib out")
                #print (f"== {node} No announcement") if not (args.csv) else False
                continue;
    
            if (not args.v4 and not args.v6):
                print ("== {}".format(node)) if not (args.csv) else False
            if (args.v4):
                if any("in-open ipv4" in s for s in output):
                    print ("== {}".format(node)) if not (args.csv) else False
            if (args.v6):
                if any("in-open ipv6" in s for s in output):
                    print ("== {}".format(node)) if not (args.csv) else False
             
            for line in (output):
                if  (args.v4):
                    if (" in-open ipv4" in line):
                        route_search= re.search('neighbor\s+(.*)\s+local-ip+.*peer-as\s+(\d+)\s+router-id+.*in-open ipv\d\sunicast\s+(.*?)\s+next-hop self\s+(.*)',line,re.IGNORECASE)
                        if (args.csv):
                            print ("{},{},{},{},{}".format(node,route_search.group(3),route_search.group(2),route_search.group(1),route_search.group(4)))
                        else:
                            print ("neighbor {} prefix {} {} ".format(route_search.group(1),route_search.group(3),route_search.group(4)))

                if  (args.v6):
                    if (" in-open ipv6" in line):
                        route_search = re.search('neighbor\s+(.*)\s+local-ip+.*peer-as\s+(\d+)\s+router-id+.*in-open ipv\d\sunicast\s+(.*?)\s+.*',line,re.IGNORECASE)
                        if (args.csv):
                            print ("{},{},{},{},{}".format(node,route_search.group(3),route_search.group(2),route_search.group(1),route_search.group(4)))
                        else:
                            print ("neighbor {} prefix {} {} ".format(route_search.group(1),route_search.group(3),route_search.group(4)))

                        
                if (not args.v4 and not args.v6):
                        route_search = re.search('neighbor\s+(.*)\s+local-ip+.*in-open ipv\d\sunicast\s+(.*?)\s+next-hop self\s+(.*)',line,re.IGNORECASE)
                        if (args.csv):
                            print ("{},{},{},{},{}".format(node,route_search.group(3),route_search.group(2),route_search.group(1),route_search.group(4)))
                        else:
                            print ("neighbor {} prefix {} {} ".format(route_search.group(1),route_search.group(3),route_search.group(4)))


    # add route (prefix) in BGP
    elif (args.add):
        logging.info(f"=== ADD ===")
        for node in args.target:
            logging.info("finding neighbor for %s", node)
            cmd = "exabgpcli show neighbor summary"
            output = run_cmd(node,cmd)
            if (not output):
                logging.info(f"No neighbors found at [{node}]")
                continue;
    
            output = parse_peers(output)
            neighbor_list = [neighbor['ip'] for neighbor in output]
            
            if (":" in args.route and not args.v6):
                print ("route IPv6 will be added to IPv4 PEERS")

            if (args.v4):
               neighbor_list = [ip for ip in neighbor_list  if ':' not in ip]
    
            elif (args.v6):
               neighbor_list = [ip for ip in neighbor_list  if ':'  in ip]
    
            logging.info(f"neighbor_list of {node} ==> {neighbor_list}")
    
            # prepare the cmd
            cmd = "announce route {} next-hop self".format(args.route)
    
            # prepend - if prepend is set update the exabgpcli cmd
            if (args.prepend):
                n_preprend = int(args.prepend)
                n_preprend = n_preprend + 1
                prepend = "1149 "
                prepend=prepend*n_preprend
                cmd = "announce route {} next-hop self as-path [{}]".format(args.route,prepend)
                logging.info(f"announce route {args.route} next-hop self as-path [{prepend}]")
        
            # run command in each neighbor
            for neighbor in neighbor_list:
                cmd_exec = "exabgpcli neighbor {} ".format(neighbor)
                cmd_exec = cmd_exec+" " + cmd
                print ("CMD={}".format(cmd_exec))
                logging.info(cmd_exec)
                output = run_cmd(node,cmd_exec)
    
    elif (args.cmd): 
        logging.info(f"=== CMD ===")
        for node in args.target:
            logging.info("finding neighbor for {}".format(node))
            cmd = "exabgpcli show neighbor summary"
            output = run_cmd(node,cmd)
            if (not output):
                logging.info(f"No neighbors found at [{node}]")
                continue;
    
            output = parse_peers(output)
            neighbor_list = [neighbor['ip'] for neighbor in output]
            logging.info(f"neighbor_list of {node} ==> {neighbor_list}")

            #if (args.v4):
            #   neighbor_list = [ip for ip in neighbor_list  if ':' not in ip]
    
            # default apply to IPv4
            if (args.v6):
               neighbor_list = [ip for ip in neighbor_list  if ':'  in ip]
            else:
               neighbor_list = [ip for ip in neighbor_list  if ':' not in ip]

            logging.info(f"neighbor_list of {node} ==> {neighbor_list}")
    
            #cmd = "announce route 145.90.8.0/24 next-hop self community 100:667"
        
            # run command in each neighbor
            for neighbor in neighbor_list:
                cmd_exec = "exabgpcli neighbor {} ".format(neighbor)
                cmd_exec = cmd_exec+" " + args.cmd
                print ("CMD={}".format(cmd_exec))
                logging.info(cmd_exec)
                output = run_cmd(node,cmd_exec)
    
    elif (args.listnodesannounce):
        logging.info(f"=== nodes-with-announces ===")
        if args.debug: print  ("list nodes") 
        result_array = []

        # Get all announcement on all Nodes
        for node in args.target:
            logging.info(f"=== nodes-with-announces:: {node} ===")
            cmd = "exabgpcli show adj-rib out extensive"

            logging.info(f"nodes-with-announces:: {node} Go Run [{cmd}]")
            output = run_cmd(node,cmd)
            logging.info(f"nodes-with-announces:: {node} output [{output}]")

            if (not output):
                logging.info(f"nodes-with-announces:: {node} No announces (not output)==> {output}")
                continue;
            else:
                for line in (output):
                    route_search = re.search('neighbor\s+(.*)\s+local-ip+.*peer-as\s+(\d+)\s+router-id+.*in-open ipv\d\sunicast\s+(.*?)\s+.*',line,re.IGNORECASE)
                    result = {
                        "neighbor": route_search.group(1),
                        "peer_as" : route_search.group(2),
                        "prefix"  : route_search.group(3),
                        "node"    : node
                    }
                    result_array.append(result)
                    logging.info(f"nodes-with-announces:: {node} found [{result}]")
    
        # build output list with result_array
        sites = []
        for route in result_array:
    
            if (args.v4):
                if ":" not in (route['prefix']):
                    sites.append(route['node'])
            elif (args.v6):
                if ":" in (route['prefix']):
                    sites.append(route['node'])
            else:
                sites.append(route['node'])
    
        label = "#ipv4+ipv6,"
        if (args.v4):
            label = "#ipv4,"
        if (args.v6):
            label = "#ipv6,"
        lst = ",".join(list(set(sites)))
        print (label+lst)

#    except KeyboardInterrupt:
#        print('Interrupted')
sys.exit(0)

### END  ###
