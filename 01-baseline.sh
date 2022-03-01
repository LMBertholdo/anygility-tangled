#!/bin/bash
###############################################################################
#  run verfploeter
#  Wed Feb 23 12:52:09 UTC 2022
#  @copyright sand-project.nl - Joao Ceron - ceron@botlog.org
#  @copyright ant.isi.edu/paaddos - Leandro Bertholdo - l.m.bertholdo@utwente.nl
###############################################################################
# Paths for regular unix binary from user aliases
shopt -s expand_aliases
# Default script settings 
source 00-globalvar.sh
# Common scripts functions definitions
source 00-functions.sh

###############################################################################
# short hitlist for testing purposes
HITLIST="$EXECDIR/tools/hitlist_example.txt"

# Origin of icmp packets
PINGER="us-mia-anycast01"

# nodes on this experiment
unset NODES
declare -a NODES
NODES+=("br-poa-anycast02")
NODES+=("us-mia-anycast01")
#NODES+=("uk-lnd-anycast02")  
NODES+=("nl-ams-anycast01")  

SLEEP=180 #fast mode

###############################################################################
### MAIN
# Initialize Logs and Dataset 
create_repository
echo "-------------------------------------------------------------------------"
echo "Sending Datasets to $REPO " | tee -a $LOG

# check the VPN Tunnel
echo "-------------------------------------------------------------------------"
echo "Checking SSH Tunnel to Master" | tee -a $LOG
check_tunnel
echo

echo "-------------------------------------------------------------------------"
echo "Checking Verfploeter connection" | tee -a $LOG
$VP_BIN cli client-list | tee -a $LOG
echo

echo "-------------------------------------------------------------------------"
echo "Cleaning routing configurations" | tee -a $LOG
$TANGLER_CLI -4 -6 -w 

# Show experiment nodes
show_nodes

#----------------------------------------------------------
# 1 - BASELINE
#----------------------------------------------------------
# Running Baseline on selected nodes

echo "-------------------------------------------------------------------------"
echo "Anycast baseline measurement started: `date` " | tee -a $LOG
echo "Activating anycast prefix $ANYCAS_PREFIX " | tee -a $LOG
advertise_on_all_nodes $ANYCAST_PREFIX 
echo "Sleeping $SLEEP"
sleep $SLEEP

echo "Checking active nodes on Tangled" | tee -a $LOG
# Preparing parameters for Verfploter and vp-cli
ACTIVE_BGP_NODES=$($TANGLER_CLI -4 --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
#BGP="baseline-$ACTIVE_BGP_NODES"
BGP="baseline"
#OUTFILE="$REPO/$BGP"
OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
echo $ACTIVE_BGP_NODES
echo ""
echo "-------" | tee -a $LOG
echo " We are generating packet in: $PINGER " | tee -a $LOG
echo " We set this BGP Policy: $BGP " | tee -a $LOG
echo " Verfploter starting..." | tee -a $LOG
run_verfploeter_looped  $OUTFILE  $PINGER

echo "-------------------------------------------------------------------------" | tee -a $LOG
echo " Baseline Finished!" | tee -a $LOG
echo " Output at $REPO/$OUTFILE" | tee -a $LOG
echo "-------------------------------------------------------------------------" | tee -a $LOG
echo ""




