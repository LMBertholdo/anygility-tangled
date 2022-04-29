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
#HITLIST="$EXECDIR/toolbox/hitlist_example.txt"
#SLEEP=30

# Origin of icmp packets
PINGER="us-mia-anycast01"

# nodes on this experiment
unset NODES
declare -a NODES
NODES+=("fr-par-anycast01")  
NODES+=("br-poa-anycast02")
NODES+=("uk-lnd-anycast02")  
NODES+=("us-mia-anycast01")
NODES+=("au-syd-anycast01")  


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
echo "Configuring Baseline" | tee -a $LOG
advertise_on_all_nodes $ANYCAST_PREFIX
echo "-------------------------------------------------------------------------"
# Show experiment nodes
show_nodes

#----------------------------------------------------------
# 2 - POSITIVE PREPEND
#----------------------------------------------------------
#
# start prepending
NUM_PREPEND=5
for num_prepend in `seq $NUM_PREPEND`;
do
    for NODE in "${NODES[@]}"
    do
        echo "-------" | tee -a $LOG
        echo "Add $num_prepend prepend on node $NODE"  | tee -a $LOG
        echo "-------" | tee -a $LOG
        $TANGLER_CLI  -A -t $NODE -r $ANYCAST_PREFIX -P $num_prepend
        echo "I'll sleep ($SLEEP) to wait for the BGP convergence"
        sleep $SLEEP

        ## run VERFPLOETER
	echo "Checking active nodes"
        ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
	#IATA=$(echo $NODE | tr "[:lower:]" "[:upper:]" | cut -d"-" -f2 )
        #BGP="$num_prepend"x"$IATA"
        #BGP="$num_prepend"x"${IATA[$NODE]}"
	BGP="prepend-positive-$num_prepend"x"-$NODE"
        #OUTFILE="$REPO/prepend-$num_prepend"x"-$NODE-$ACTIVE_BGP_NODES-$DATE_VAR"
        OUTFILE="${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
	echo "Active nodes"
        echo $ACTIVE_BGP_NODES

        echo ""
        echo "-------" | tee -a $LOG
        echo " We are generating packet in: $PINGER " | tee -a $LOG
        echo " We set this BGP Policy: $BGP " | tee -a $LOG
        echo " Verfploter starting..." | tee -a $LOG
        run_verfploeter_looped  $OUTFILE  $PINGER

        # remove the prepend
        remove_route_from_node $NODE

	# add back regular prefix announcement (with no prepend) for $NODE
        add_routes_to_node $NODE
    done
done

echo "-------------------------------------------------------------------------" | tee -a $LOG
echo " Prepend Finished!" | tee -a $LOG
echo " Output at $REPO/$OUTFILE" | tee -a $LOG
echo "-------------------------------------------------------------------------" | tee -a $LOG
echo ""


