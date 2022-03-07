#!/bin/bash
###############################################################################
# run experiments on verfploeter for catchment manipulation
#  Fri Jan 31 18:29:26 CET 2020
#  @copyright ant.isi.edu/paaddos - Leandro Bertholdo - l.m.bertholdo@utwente.nl
#  @copyright sand-project.nl - Joao Ceron - ceron@botlog.org
###############################################################################
# Paths for regular unix binary from user aliases
shopt -s expand_aliases
# Default script settings
source 00-globalvar.sh
# Common scripts functions definitions
source 00-functions.sh

###############################################################################
### Program settings
#HITLIST="$EXECDIR/tools/hitlist_example.txt"
#SLEEP=180
SLEEP=300

### pinger 
PINGER="us-mia-anycast01"

# first set (3 sites)
unset NODES
declare -a NODES
NODES+=("au-syd-anycast01")
NODES+=("us-mia-anycast01")
NODES+=("uk-lnd-anycast02")
NODES+=("fr-par-anycast01")

#NODES+=("us-was-anycast01")
#NODES+=("us-mia-anycast01")
#NODES+=("au-syd-anycast01")
#NODES+=("uk-lnd-anycast02")
#NODES+=("fr-par-anycast01")
#NODES+=("br-poa-anycast02")

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
show_nodes

# show verfploeter nodes connected
$VP_BIN cli client-list

############################################################
################# ANYCAST EXPERIMENTS ######################
############################################################

#----------------------------------------------------------
# 4 - COMMUNITIES
#----------------------------------------------------------

#
# Creating a baseline
#
echo "-------------------------------------------------------------------------"
echo "Communities measurement started: `date` " | tee -a $LOG
echo "Activating anycast prefix $ANYCAS_PREFIX " | tee -a $LOG
#  Clear all prefixes
$TANGLER_CLI -4 -w

# activate nodes
advertise_on_all_nodes $ANYCAST_PREFIX
echo "Sleeping $SLEEP"
sleep $SLEEP
echo "Checking active nodes on Tangled" | tee -a $LOG

# Preparing parameters for Verfploter and vp-cli
ACTIVE_BGP_NODES=$($TANGLER_CLI -4 --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
BGP="community-baseline"
OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"

echo "Active nodes" | tee -a $LOG
echo $ACTIVE_BGP_NODES | tee -a $LOG
echo ""
echo "-------" | tee -a $LOG
echo " We are generating packet in: $PINGER " | tee -a $LOG
echo " We set this BGP Policy: $BGP " | tee -a $LOG
echo " Verfploter starting..." | tee -a $LOG
run_verfploeter_looped  $OUTFILE  $PINGER

#
# Starting communities use
#
echo "-------"
echo "anycast service is ready for communities experiment: `date` " | tee -a $LOG
echo "-------"

# communities VULTR nodes
#Do not announce to IX peers
unset COMM
declare -a COMM
COMM+=("20473:6601") # Do not announce to IX peers
#COMM+=("20473:6000") # Do not export out of AS20473    
COMM+=("20473:6001") # prepend 1 
#COMM+=("20473:6002") # prepend 2
#COMM+=("20473:6003") # prepend 3
COMM+=("20473:64609") # Set Metric to 0 to all AS’s
COMM+=("20473:6001 20473:6003") # noixp + 3 prepend

# anycast testbed nodes
declare -a NODES_VULTR
NODES_VULTR+=("au-syd-anycast01")
NODES_VULTR+=("uk-lnd-anycast02")
NODES_VULTR+=("fr-par-anycast01")


echo "-------"
echo "Starting VULTR communites : `date` " | tee -a $LOG
echo "-------"
# start prepending
for community in "${COMM[@]}"
do
    for NODE in "${NODES_VULTR[@]}"
    do
        echo "add community $community on node $NODE"  | tee -a $LOG
        echo "-------"
        $TANGLER_CLI  -4 -t $NODE -c "announce route 145.100.118.0/23 next-hop self community [ $community ]"
        $TANGLER_CLI -a --csv | tee -a $LOG
        echo "sleep to waiting for the convergency" | tee -a $LOG
        sleep $SLEEP

	# run VERFPLOETER
        ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
    	out_comm=$( echo $community | sed "s/ /_/g" )
    	BGP="community-$out_comm"x"${IATA[$NODE]}"
        echo "BGP=$BGP" | tee -a $LOG
        OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
        echo "OUTFILE=$OUTFILE" | tee -a $LOG
        run_verfloeter $OUTFILE $PINGER


        # remove the prepend
        echo "remove community from the node $NODE" | tee -a $LOG
        remove_route_from_node $NODE 

        #add back regular prefix announcement for node
	echo "putting route back" | tee -a $LOG
        add_routes_to_node $NODE
    done
done

echo "-------"
echo "anycast communities VULTR finished: `date` " | tee -a $LOG
echo "-------"



### Communities AMPATH

echo "-------"
echo "Starting AMPATH communities: `date` " | tee -a $LOG
echo "-------"

# communities
unset COMM
declare -a COMM
COMM+=("20080:700") #no-peers
COMM+=("20080:701") #no-customer
COMM+=("20080:702") #no-upstream
COMM+=("20080:110") #lower localpref
#COMM+=("20080:801") #1x prepend
COMM+=("20080:802") #2x prepend
#COMM+=("20080:803") #3x prepend
#COMM+=("20080:804") #4x prepend
COMM+=("20080:110 20080:700 20080:803")

# ensure that all the prefix are active and running
$TANGLER_CLI -4 -w
sleep 300

advertise_on_all_nodes
$TANGLER_CLI -4 -a --csv

# start prepending
for community in "${COMM[@]}"
do
        NODE="us-mia-anycast01"
        echo "add community $community on node $NODE"  | tee -a $LOG
        echo "-------"
        $TANGLER_CLI  -4 -t $NODE -c "announce route 145.100.118.0/23 next-hop self community [ $community ]"
        $TANGLER_CLI -a --csv | tee -a $LOG
        echo "sleep to waiting for the convergency"
        sleep $SLEEP

	# run VERFPLOETER
        ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
    	#BGP="positive-$community"x"$( echo $NODE | sed "s/-anycast[0-9][0-9]//g" )
    	out_comm=$( echo $community | sed "s/ /_/g" )
    	BGP="community-$out_comm"x"${IATA[$NODE]}"
        echo "BGP=$BGP"
        OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
        echo "OUTFILE=$OUTFILE"
        run_verfloeter $OUTFILE $PINGER

        # remove the prepend
        echo "remove community from the node $NODE"
        remove_route_from_node $NODE 
        sleep 30

        #add back regular prefix announcement for node
        add_routes_to_node $NODE
done

echo "-------"
echo "Finished  AMPATH communities: `date` " | tee -a $LOG
echo "-------"
echo "-------"
echo "Ended Communities experiment: `date` " | tee -a $LOG
echo "-------"

