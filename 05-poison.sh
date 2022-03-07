#!/bin/bash
###############################################################################
#  run baseline for anycast testbed
#  Fri Jan 31 18:29:26 CET 2020
#  @copyright ant.isi.edu/paaddos - Leandro Bertholdo - l.m.bertholdo@utwente.nl
#  @copyright sand-project.nl - Joao Ceron - ceron@botlog.org
###############################################################################

# INCLUDES
shopt -s expand_aliases
source 00-globalvar.sh
source 00-functions.sh

###############################################################################
### Program settings
#HITLIST="$EXECDIR/toolbox/hitlist_example.txt"
PINGER="us-mia-anycast01"
#SLEEP=60
ANYCAST_PREFIX="145.100.118.0/23"

# REDefine nodes (from 00-globalvar)
unset NODES
declare -a NODES
NODES+=("br-poa-anycast02")
NODES+=("us-mia-anycast01")
NODES+=("nl-ams-anycast01")


###############################################################################
### Functions
# ----------------------------------------------------------------------------

poison_vp_outfile_name(){
	echo "------- Verfploeter setup -------" 		| tee -a $LOG

	ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g" | sed "s/..-//g") 
	echo "ACTIVE_BGP_NODES [$ACTIVE_BGP_NODES]" | tee -a $LOG

	#outfile
	OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}" 
	echo "OUTFILE [$OUTFILE]" | tee -a $LOG
}

run_poison(){
	local aspoison="1149_"$1"_1149"
	echo "------- poison [ $aspoison ] -----"
	
	tcmd poison us-mia-anycast01 $aspoison $ANYCAST_PREFIX
	sleep $SLEEP

	# BGP Policy
	BGP="poison-"$( echo $1 | sed "s/_/-/g" )

	# Assembly verfploeter output file name
	poison_vp_outfile_name 

	# Run verfploeter
	run_verfloeter  "$OUTFILE" "$PINGER"

}


###############################################################################
### MAIN
###############################################################################
# create repository dir
[ ! -d $REPO ] && mkdir $REPO

# update symlink
dir_=`dirname $REPO`
ln -sfn $REPO $dir_/last

echo "logfile in: $LOG"
## initial setup
date | tee -a $LOG

# check the VPN Tunnel
check_tunnel

# show defined nodes
show_nodes | tee -a $LOG

# show verfploeter nodes connected
$VP_BIN cli client-list | tee -a $LOG


############################################################
## Anycast distribution - regular monitoring - BASELINE
############################################################

# CLEANING ALL
# this will withdraw all the prefix over all the nodes
echo "removing all routes on all known nodes"
$TANGLER_CLI -4 -6 -w 

echo "-------------------------------------------------------------------------"
echo "Anycast baseline measurement started: `date` " | tee -a $LOG
echo "Activating anycast prefix $ANYCAS_PREFIX " | tee -a $LOG
advertise_on_all_nodes $ANYCAST_PREFIX
BGP="poison-baseline"
poison_vp_outfile_name "poison-baseline"
run_verfploeter "$OUTFILE" "$PINGER"
sleep $SLEEP

# prepend one in MIA
BGP="poison-1xMIA"
tcmd prepend us-mia-anycast01 1149_1149 $ANYCAST_PREFIX
poison_vp_outfile_name "1149_1149"
sleep $SLEEP
run_verfploeter "$OUTFILE" "$PINGER"

# prepend two in MIA
BGP="poison-2xMIA"
tcmd prepend us-mia-anycast01 1149_1149_1149 $ANYCAST_PREFIX
poison_vp_outfile_name "1149_1149_1149"
sleep $SLEEP
run_verfploeter "$OUTFILE" "$PINGER"

#
# Do poison on MIA + run verfploeter
# 
run_poison 63221  #FL-IX  
run_poison 24115  #EQ-MIA

run_poison 2914	  #SPRINT
run_poison 6939   #HURRICANE

run_poison 7018   #ATT
run_poison 701    #Verizon
run_poison 6762   #TISparke
run_poison 3257   #GTT

run_poison 6461   #ZAYO
run_poison 12953  #reuters
run_poison 174    #cogent
run_poison 1239   #spring-link
run_poison 1273   #vodafone
run_poison 1299   #telia
run_poison 3320   #deutch telecom
run_poison 3356   #level3
run_poison 5511   #orange
run_poison 6453   #tata

run_poison 63221_24115 #equinix at fl-ix

run_poison  1916   #RNP
run_poison  1251   #ANSP
run_poison  16735  #Algar
run_poison  262589 #Internexa


echo "-------"
echo "finished poison experiment"
echo "-------"
echo
    
