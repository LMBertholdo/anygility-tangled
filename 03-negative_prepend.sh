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

# Origin of icmp packets
PINGER="us-mia-anycast01"

# nodes on this experiment
unset NODES
declare -a NODES
NODES+=("uk-lnd-anycast02")
NODES+=("fr-par-anycast01")
NODES+=("au-syd-anycast01")

#SLEEP=60 #fast mode

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
# 3 - NEGATIVE PREPEND
#----------------------------------------------------------

MAX_NEGATIVE_PREPENDS=3

for WORKING_NODE in "${NODES[@]}"
do
	# We will prepend all nodes except WORKING_NODE
	echo "-------"
	echo "WORKING_NODE ===> $WORKING_NODE"
	echo "(re) Configuring Baseline"
	echo "-------"
	# Announce on working_node 
	advertise_on_node $WORKING_NODE $ANYCAST_PREFIX

        # IATA=$(echo $WORKING_NODE | tr "[:lower:]" "[:upper:]" | cut -d"-" -f2 )
	for num_prepend in `seq $MAX_NEGATIVE_PREPENDS`
	do 
        	#BGP="-$num_prepend"x"$IATA"
		BGP="-$num_prepend"x"${IATA[$WORKING_NODE]}"
		echo "-------"
		echo "$num_prepend negative Prepend for node $WORKING_NODE ( ${BGP} )" | tee -a $LOG
                echo "-------"

	        # Prepend other sites
	        for node in "${NODES[@]}"
                do
                    if [ $WORKING_NODE == $node ]; then
                        # do not prepend working node
                        echo "ignoring node $WORKING_NODE"
                        continue;
                    fi

                    echo "Adding [$num_prepend] prepend to [$node]"
                    $TANGLER_CLI  -A -t $node -r $ANYCAST_PREFIX -P $num_prepend
		done

		# Wait for routing settlement
	        echo "sleeping $SLEEP s "
	        sleep $SLEEP
		
		# Show routes
		#parallel_show_routes
		$TANGLER_CLI -a --csv

		# run Verfploeter
	        ACTIVE_BGP_NODES=$($TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g")
		OUTFILE="negative_${BGP}${ACTIVE_BGP_NODES}#${DATE_VAR}"
		run_verfploeter_looped  $OUTFILE  $PINGER

		# Remove routes
		#parallel_withdraw_all_nodes
	done
done


echo "-------------------------------------------------------------------------" | tee -a $LOG
echo " Negative Prepend Finished!" | tee -a $LOG
echo " Output at $REPO" | tee -a $LOG
echo "-------------------------------------------------------------------------" | tee -a $LOG
echo ""



