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
HITLIST="$EXECDIR/tools/hitlist_example.txt"
SLEEP=180

### pinger 
PINGER="us-mia-anycast01"

# first set (3 sites)
unset NODES
declare -a NODES
NODES+=("au-syd-anycast01")
NODES+=("us-mia-anycast01")
NODES+=("uk-lnd-anycast02")

# second set ( 5 sites ) 
# LAX' 'MIA' 'LHR' 'SYD' 'CDG' 
#NODES+=("us-los-anycast01")
#NODES+=("fr-par-anycast01")

# third set ( 7 sites ) 
# ['POA' 'LHR' 'SYD' 'ENS' 'CDG' 'MIA']
#NODES+=("br-poa-anycast01")
#NODES+=("nl-ens-anycast02")


###############################################################################
### Functions
# 
# # ----------------------------------------------------------------------------
# # show nodes used in this experiment
# show_nodes(){
# 
#     echo "we are using ${#NODES[@]} nodes in this experiment"; 
#     for NODE in "${NODES[@]}"
#     do
#         echo "$NODE"
#     done
# }
# 
# # ----------------------------------------------------------------------------
# # run verfploeter and collect results
# run_verfloeter(){
#    OUTFILE=$1
#    [ ! -d $REPO ] && mkdir $REPO
#    echo $OUTFILE
#    echo "$VERFPLOETER_BIN cli start $ORIGIN $ANYCAST_ADDRESS  $HITLIST  -a $ASN_DB -c $GEO_DB  > $OUTFILE"
#    $VERFPLOETER_BIN cli start $ORIGIN $ANYCAST_ADDRESS  $HITLIST  -a $ASN_DB -c $GEO_DB  > $OUTFILE
#    numlines=$(wc -l $OUTFILE | awk '{print $1}')
#    if [ "$numlines" -gt 1000 ]; then
#             echo "-s $NODE -v -b \"$BGP\" -f \"$OUTFILE\" " > $OUTFILE.meta
#             $TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g" > $OUTFILE.routing
#             $TANGLER_CLI -a --csv >> $OUTFILE.routing
# 
#             # stats
#             $VPCLI -f $OUTFILE  -q  > $OUTFILE.stats  
# 
#             gzip $OUTFILE &
#             result="OK"
# 
#    else
#         echo "output presented a low number of lines [$numlines]"
#         result="ERROR"
#         gzip  $OUTFILE &
#    fi
#    # build convertion line
#    echo "$VPCLI -s $ORIGIN  -b \"$BGP\" -g $IP2LOCATION  -f $OUTFILE.gz -n -q " > $OUTFILE.meta-convert
# 
# }
# 
# # ----------------------------------------------------------------------------
# check_tunnel(){
#     # check ssh tunnel
#     # we have an overlay net (vpn) to collect the results from vp nodes
#     result=`ps gawx | grep ssh | grep 50001 | wc -l`
#     if [ "$result" -lt 1 ]; then
#         echo "setting tunnel ssh to master"
#         ssh -f  -N  -L 50001:localhost:50001 master
#     fi
# }
# 
# # ----------------------------------------------------------------------------
# set_announces_in_all_nodes(){
#     # add regular announcement for all the nodes
#     for NODE in "${NODES[@]}"
#     do
#         # add prefix announcement for $NODE
#         echo "add prefix announcement for $NODE"
#         echo "-------"
#         $TANGLER_CLI  -t $NODE -A -r $ANYCAST_PREFIX 
#     done
#     $TANGLER_CLI -4 -a --csv
#     echo "I'll sleep for $SLEEP to wait for the BGP converge"
#     sleep $SLEEP
# }
# # ----------------------------------------------------------------------------
# withdraw_all_running_nodes(){
#     echo "Cleaning all the announcements"
#     # withdraw routes from all the nodes
#     for NODE in "${NODES[@]}"
#     do
#         $TANGLER_CLI -t $NODE -w  -4
#     done
#     sleep 10
# }
# 
# # ----------------------------------------------------------------------------
# add_routes_to_node(){
#     curr_node=$1
#     echo "-------"
#     echo "add prefix announcement for $curr_node" | tee -a $LOG
#     echo "-------"
#     $TANGLER_CLI -4 -t $curr_node  -A -r "145.100.118.0/23"
# }
# 
# # ----------------------------------------------------------------------------
# remove_route_from_node(){
#     curr_node=$1
#     echo "-------"
#     echo "remove announcement from $curr_node" | tee -a $LOG
#     echo "-------"
#     $TANGLER_CLI -4 -t $curr_node  -w 
#     sleep 30
# }

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
###################### UNICAST TEST ########################
############################################################
# Check the node visibility. Each node should be able to get replies
# from all the hitlist.

# clean all the routes, not only for the nodes running 
$TANGLER_CLI -4 -6 -w

echo "-------"
echo "unicast test started: `date` " | tee -a $LOG
echo "-------"

for NODE in "${NODES[@]}"
do
    echo "unicast ◢  $NODE ◣"
    add_routes_to_node $NODE

    BGP="unicast-"$( echo $NODE | sed "s/-anycast[0-9][0-9]//g" )
    echo "BGP=$BGP"

    ACTIVE_BGP_NODES=$($TANGLER_CLI -4 --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
    OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
    echo "OUTFILE=$OUTFILE"

    run_verfloeter $OUTFILE $PINGER

    echo $result
    remove_route_from_node $NODE
done

echo "-------"
echo "unicast test finished: `date` " | tee -a $LOG
echo "-------"

############################################################
################# ANYCAST EXPERIMENTS ######################
############################################################

#----------------------------------------------------------
# 4 - COMMUNITIES
#----------------------------------------------------------

# ensure that all the prefix are active and running
$TANGLER_CLI -4 -w
#set_announces_in_all_nodes
advertise_on_all_nodes
$TANGLER_CLI -4 -a --csv
echo "-------"
echo "anycast service is ready for communities experiment: `date` " | tee -a $LOG
echo "-------"

# communities
#Do not announce to IX peers
declare -a COMM
COMM+=("20473:6601") # Do not announce to IX peers
COMM+=("20473:6000") # Do not export out of AS20473    
COMM+=("20473:6001") # prepend 1 
COMM+=("20473:6002") # prepend 2
COMM+=("20473:6003") # prepend 3
COMM+=("20473:64609") # Set Metric to 0 to all AS’s

#NTT: AS2914

# anycast testbed nodes
declare -a NODES_VULTR
NODES_VULTR+=("au-syd-anycast01")
NODES_VULTR+=("uk-lnd-anycast02")
NODES_VULTR+=("fr-par-anycast01")


# start prepending
for community in "${COMM[@]}"
do
    for NODE in "${NODES_VULTR[@]}"
    do
        echo "add community $community on node $NODE"  | tee -a $LOG
        echo "-------"
        $TANGLER_CLI  -4 -t $NODE -c "announce route 145.100.118.0/23 next-hop self community $community"
        $TANGLER_CLI -a --csv | tee -a $LOG
        echo "sleep to waiting for the convergency"
        sleep $SLEEP

	# run VERFPLOETER
        ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
    	BGP="positive-$community"x"$( echo $NODE | sed "s/-anycast[0-9][0-9]//g" )
        echo "BGP=$BGP"
        OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
        echo "OUTFILE=$OUTFILE"
        run_verfloeter $OUTFILE $PINGER


        # remove the prepend
        echo "remove community from the node $NODE"
        remove_route_from_node $NODE 

        #add back regular prefix announcement for node
        add_routes_to_node $NODE
    done
done

echo "-------"
echo "anycast communities experiment finished: `date` " | tee -a $LOG
echo "-------"



### Communities AMPATH


# communities
declare -a COMM
COMM+=("20080:700")
COMM+=("20080:701")
COMM+=("20080:702")
COMM+=("20080:700 20080:702")
COMM+=("20080:662")

# ensure that all the prefix are active and running
$TANGLER_CLI -4 -w
sleep 30
#set_announces_in_all_nodes
advertise_on_all_nodes
$TANGLER_CLI -4 -a --csv

# start prepending
for community in "${COMM[@]}"
do
        NODE="us-mia-anycast01"
        echo "add community $community on node $NODE"  | tee -a $LOG
        echo "-------"
        $TANGLER_CLI  -4 -t $NODE -c "announce route 145.100.118.0/23 next-hop self community [$community]"
        $TANGLER_CLI -a --csv | tee -a $LOG
        echo "sleep to waiting for the convergency"
        sleep $SLEEP

	# run VERFPLOETER
        ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
    	BGP="positive-$community"x"$( echo $NODE | sed "s/-anycast[0-9][0-9]//g" )
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


