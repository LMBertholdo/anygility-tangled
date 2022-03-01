#!/bin/bash
###############################################################################
### Functions
###############################################################################
# Debug Function
#  Redeclaring printf and/or echo to show nothing 
#  (comment lines below to enable debug)
printf() { :; }     # maximum debug
#echo() { :; }      # normal verbose

# Check connection with Master node to get verfpleoter data
check_tunnel(){
	local result
    # check ssh tunnel
    # we have an overlay net (vpn) to collect the results from vp nodes
    result=`ps gawx | grep ssh | grep 50001 | wc -l`
    if [ "$result" -lt 1 ]; then
        echo "setting tunnel ssh to master"
        ssh -f  -N  -L 50001:localhost:50001 master
    fi

    # Check nomad connection to restart Vploeter if needed
    result=`ps gawx | grep ssh | grep 4646 | wc -l`
    if [ "$result" -lt 1 ]; then
        echo "setting tunnel ssh to master"
        ssh -f  -N  -L 4646:10.8.0.1:4646 master
    fi
}

# ----------------------------------------------------------------------------
# create a repository on datasets/last and start Logs
create_repository(){
    local dir_

    # create repository dir
    [ ! -d $REPO ] && mkdir $REPO
    
    # update symlink
    dir_=`dirname $REPO`
    ln -sfn $REPO $dir_/last
    
    ## initial print
    echo "logfile in: $LOG"
    date -u | tee -a $LOG
}

# ----------------------------------------------------------------------------
# Restart Verfploeter using Nomad
restart_verfploeter_nomad(){
    echo "**** RESTARTING VERFPLOETER ****"
    echo "**** RESTARTING VERFPLOETER ****"
    echo "**** RESTARTING VERFPLOETER ****"

    #nomad status
    # Stop verfploeter
    echo "**** nomad stop verfploeter ****"
    nomad stop verfploeter

    # Clean verfploeter instance
    echo "**** curl -X PUT http://localhost:4646/v1/system/gc ****"
    curl -X PUT http://localhost:4646/v1/system/gc

    # Start new verfploeter
    echo "**** nomad run verfploeter.nomad ****"
    nomad run verfploeter.nomad

    # Give some time and check
    sleep 60
    $VP_BIN cli client-list
}


# ----------------------------------------------------------------------------
# run verfploeter and collect results
# need global RETVAL to return value
run_verfploeter(){
    local vp_out=$1
    local vp_src=$2
    local numlines
    local bgp

    echo "Starting verfploeter..."
    if [ -z "$VP_BIN" ]; then
	    echo "ERROR:: Need to set VP_BIN (Verfploter binary)"
	    exit 1
    fi

    [ ! -d $REPO ] && mkdir $REPO
    
    # Routes
    (	echo "#policy,$BGP" > $REPO/$vp_out.routing
        $TANGLER_CLI --nodes-with-announces |  sed "s/-anycast[0-9][0-9]//g" >> $REPO/$vp_out.routing
        $TANGLER_CLI -a --csv >> $REPO/$vp_out.routing ) 

    echo "$VP_BIN cli start $vp_src $ANYCAST_ADDRESS  $HITLIST  -a $ASN_DB -c $GEO_DB  > $REPO/$vp_out.csv" | tee -a $LOG
    $VP_BIN cli start $vp_src $ANYCAST_ADDRESS  $HITLIST  -a $ASN_DB -c $GEO_DB  > $REPO/$vp_out.csv

    numlines=$(wc -l $REPO/$vp_out.csv | awk '{print $1}')
    if [ "$numlines" -gt 1000 ]; then
        # meta
	bgp="$BGP"
        echo "$VPCLI -s $vp_src  -b \\\""$BGP"\\\"  -f $REPO/$vp_out.csv.gz" > $REPO/$vp_out.meta

	# build convertion line (normalize)
        echo "$VPCLI -s $vp_src  -b \\\""$BGP"\\\" -g $IP2LOCATION  -f $REPO/$vp_out.csv.gz -n" > $REPO/$vp_out.meta-convert

        # stats
        ( $VPCLI -q -b \"$BGP\" -f $REPO/$vp_out.csv --csv  >> $REPO/$vp_out.stats )  
        result="OK"
        RETVAL="OK" #global var to return error on VP

        ( gzip -f $REPO/$vp_out.csv )  &

        echo
    else
         echo "------------------------------------------------------------------" | tee -a $LOG
         echo "### ERROR:: output presented a LOW NUMBER OF LINES [$numlines] ###" | tee -a $LOG
         echo "------------------------------------------------------------------" | tee -a $LOG

        ( gzip -f $REPO/$vp_out.csv ) &

         result="ERROR"
         RETVAL="ERROR"

    fi

}

# Just to save time from wrong writing to some users
run_verfloeter(){
    #run_verfploeter $1 $2
    run_verfploeter_looped $1 $2
}

# ----------------------------------------------------------------------------
# run verfploeter several times can break on servers with low resources
# running verfploter_looped restart verfploeter to try again before give up
# Need global RETVAL definition to get the error of VERFPLOETER
run_verfploeter_looped(){
    local vp_out=$1
    local vp_src=$2
    local numlines

    for i in {1..5} ; do
    	echo "**** RUNNING VERFPLOETER LOOPED [$i] ****"
        run_verfploeter $vp_out $vp_src  
    
        if [ "$RETVAL" == "OK" ]; then
            break
        else
            echo "ERROR: Trying Verfploeter again in 5 minutes"
            echo "**** NEED TO DO::: RESTARTING VERFPLOETER / NOMAD *******"
            restart_verfploeter_nomad
        fi
    done

    if [ "$RETVAL" == "ERROR" ]; then
            echo "*******  I CANT RESTART VERFPLOETER   ******* "
            echo "*******  GIVING UP AFTER (5) ATTEMPTS  ******* "
            exit 1
    fi
}


# ----------------------------------------------------------------------------
# show nodes used in this experiment (listed on $NODES)
# NODES variable can be set inside each script to chose a nodes subset
show_nodes(){
    printf "[show_nodes]\n" 
    echo "we are using ${#NODES[@]} nodes in this experiment";
    for NODE in "${NODES[@]}"
    do
        echo "$NODE"
    done
}

# ----------------------------------------------------------------------------
# All Functions below are parallelized function and 5x faster than tangled-cli
# ----------------------------------------------------------------------------
# List all routes active on each node
show_all_nodes(){
    parallel_show_routes
}

parallel_show_routes(){
    local pid pids

    printf "[show_all_nodes]\n" 
    echo "Showing all routes..."
    for NODE in "${NODES[@]}"; do
        (  $TANGLER_CLI  -t $NODE -a   ) &
        pids[${i}]=$!
        ((i++))
        printf "[show_all_nodes]: %s pid=%s\n" $NODE $!
    done
    # Wait spawned processes to finished
    for pid in ${pids[*]}; do
        wait $pid
        printf "[show_all_nodes]: ended:%s\n" $pid
    done
}

# ----------------------------------------------------------------------------
# Remove a prefix on a site anycast - all routes are removed if not specified
withdraw_on_node(){
    local node=$1
    local pfx=$2      #default is withdraw ALL_ROUTES
    local cmd
    local pid pids

    printf "[withdraw_on_node]\n" 
    if [[ "$node" == "" ]] ; then
        echo "ERROR: Node not specified while calling __withdraw_on_node__"
        exit 1
    else
        if [ "$pfx" ]; then
            cmd="-t $node -r $pfx -w"
            echo "Removing route [$pfx] on node [$node]" | tee -a $LOG
        else
            cmd="-t $node -w"
            echo "Removing all prefixes on node [$node]" | tee -a $LOG
        fi
        $TANGLER_CLI $cmd
    fi
}

# ----------------------------------------------------------------------------
# Clear a route on all running nodes. If no route, all routes will be removed.
# Just execute on var $NODES - not ALL nodes
withdraw_on_all_nodes(){
    parallel_withdraw_all_nodes
}
parallel_withdraw_all_nodes(){
    local pfx=$1
    local cmd
    local pid pids

    printf "[withdraw_on_all_nodes]\n" 
    if [ "$pfx" ]; then
        cmd="-r $pfx -w"
        echo "Cleaning all the Sites announcements of [$pfx]" | tee -a $LOG
    else
        cmd="-w"
        echo "Cleaning all Sites Routes"
    fi
    # withdraw routes from all the nodes
    for NODE in "${NODES[@]}"
    do
        ( $TANGLER_CLI -t $NODE $cmd ) &
        pids[${i}]=$!
        ((i++))
    done 

    # Wait spawned processes to finished
    for pid in ${pids[*]}; do
        wait $pid
    done
}

# ----------------------------------------------------------------------------
# announce a prefix on a node. If prefix is not specified it announce ANYCAST_PREFIX
advertise_on_node(){
    local node=$1
    local pfx=$2      #default is announce ANYCAST_PREFIX

    printf "[advertise_on_node]\n" 
    if [[ "$node" == "" ]]; then
        echo "ERROR: Node not specified while calling __annouce_on_node__"
        exit 1
    else
        if [[ "$pfx" == "" ]]; then
            pfx=$ANYCAST_PREFIX
        fi    
        echo "Announce route [$pfx] on node [$node]" | tee -a $LOG
        $TANGLER_CLI -t $node -r $pfx -A
    fi
}

# ----------------------------------------------------------------------------
# poison a prefix on a node. If prefix is not specified it announce ANYCAST_PREFIX
poisoning_on_node(){
    local node=$1
    local aspath=$2
    local pfx=$3      #default is announce ANYCAST_PREFIX

    printf "[poisoning_on_node]\n" 
    if [[ "$node" == "" ]]; then
        echo "ERROR: Node not specified while calling __annouce_on_node__"
        exit 1
    else
        if [[ "$pfx" == "" ]]; then
            pfx=$ANYCAST_PREFIX
        fi    
        if [[ "$aspath" == "" ]]; then
                echo "ERROR: __poisoning_on_node__ without AS-PATH specified!"
                exit 1
        else
            echo "Announce Poison [$aspath] [$pfx] on node [$node]" | tee -a $LOG
            #$TANGLER_CLI -t $node -r $pfx -A
            ASPATH=$( echo $aspath | sed "s/_/ /g" )
            #echo "$TANGLER_CLI -t $node -c announce route $pfx next-hop self as-path [ $ASPATH ]"
            $TANGLER_CLI  -t $node -c "announce route $pfx next-hop self as-path [ $ASPATH ]" | tee -a $LOG
        fi
    fi
}

# ----------------------------------------------------------------------------
# poison a prefix on a node. If prefix is not specified it announce ANYCAST_PREFIX
advertise_ixp_on_node(){
    local node=$1
    local pfx=$2      #default is announce ANYCAST_PREFIX
    local aspath=$3

    printf "[advertise_ixp_on_node]\n" 
    if [[ "$node" == "" ]]; then
        echo "ERROR: Node not specified while calling __advertise_ixp_on_node__"
        exit 1
    else
        if [[ "$pfx" == "" ]]; then
            pfx=$ANYCAST_PREFIX
        fi    
        if [[ "$aspath" == "" ]]; then
            ASPATH='1149'
        else
            # is poisoned
            ASPATH=$( echo $aspath | sed "s/_/ /g" )
        fi

        echo "Announce to IXP on node [$node] [$pfx] [$ASPATH] " | tee -a $LOG

        # Set BGP-COMM to IXP to avoid leaking.
        if [[ " ${IXP_DIRECT[@]} " =~ " ${node} " ]]; then
            BGPCOMM=${BRCOMM[*]}
            echo "ssh $node \"exabgpcli neighbor $BIRD announce route $pfx next-hop self as-path [ $ASPATH ] community [ ${BGPCOMM[*]} ]\" " | tee -a $LOG
            ssh $node "exabgpcli neighbor $BIRD announce route $pfx next-hop self as-path [ $ASPATH ] extended-community [ ${BGPCOMM[*]} ]" | tee -a $LOG

        elif [[ " ${IXP_VULTR[@]} " =~ " ${node} " ]]; then
            BGPCOMM=${VCOMM[*]}
            $TANGLER_CLI  -4 -t $node -c "announce route $pfx next-hop self as-path [ $ASPATH ] community [ ${BGPCOMM[*]} ]"       

        elif [[ " ${IXP_HEFICED[@]} " =~ " ${node} " ]]; then
            BGPCOMM=$HCOMM[*]}    
            $TANGLER_CLI  -4 -t $node -c "announce route $pfx next-hop self as-path [ $ASPATH ] community [ ${BGPCOMM[*]} ]"       
        fi        
    fi
}

# ----------------------------------------------------------------------------
# Announce a prefix on running nodes, or ANYCAST_PREFIX if not defined.
advertise_on_all_nodes(){
    local pfx=$1
    local pid pids

    printf "[advertise_on_all_nodes]\n" 
    if [ "$pfx" == "" ]; then
        pfx=$ANYCAST_PREFIX
    fi

    # add regular announcement for all the nodes
    for NODE in "${NODES[@]}"
    do
        # add prefix announcement for $NODE
        echo "-------"
        echo "add prefix announcement for $NODE"
        echo "$TANGLER_CLI  -t $NODE -A -r $pfx"
        $TANGLER_CLI  -t $NODE -A -r $pfx
    done
}

# ----------------------------------------------------------------------------
# Announce a prefix on running nodes, or ANYCAST_PREFIX if not defined.
parallel_advertise_on_all_nodes(){
    local pfx=$1
    local pid pids

    printf "[advertise_on_all_nodes]\n"
    if [ "$pfx" == "" ]; then
        pfx=$ANYCAST_PREFIX
    fi

    # add parallel announcement for all the nodes
    for NODE in "${NODES[@]}"
    do
            ( echo "add prefix announcement for $NODE"
            # echo "-------"
            # echo "$TANGLER_CLI  -t $NODE -A -r $pfx"
            $TANGLER_CLI  -t $NODE -A -r $pfx    ) &
        pids[${i}]=$!
        ((i++))
    done
    # Wait spawned processes to finished
    for pid in ${pids[*]}; do
        wait $pid
    done
}


# ----------------------------------------------------------------------------
# Tangled command mode 
# Just work on nodes activated by NODES[@] not all nodes as tangled-cli
tcmd(){
    if [[ $1 == 'adv' ]] ; then
        echo "Advertisement a prefix to all nodes"
        advertise_on_all_nodes $2
    
    elif [[ $1 == 'rm' ]] ; then
        echo "Remove a prefix on all nodes"
        withdraw_on_all_nodes $2
    
    elif [[ $1 == 'del' ]] ; then
        echo "Withdraw $2 $3"
        withdraw_on_node $2 $3 
    
    elif [[ $1 == 'add' ]] ; then
        # node pfx
        echo "Announce $2 on $3"
        advertise_on_node $2 $3 
    
    elif [[ $1 == 'poison' ]] || [[ $1 == 'prepend' ]] ; then 
        # node as-path pfx
        echo "Announce $2 on $3"
        poisoning_on_node $2 $3 $4
    
    elif [[ $1 == 'ixp' ]] ; then 
        # node [pfx] [as-path]
        echo "Announce on IXP at $2"
        advertise_ixp_on_node $2 $3 $4 
    
    else
        echo "default: Show"
        show_all_nodes
    fi
}

# ----------------------------------------------------------------------------
add_routes_to_node(){
    curr_node=$1
    echo "-------"
    echo "add prefix announcement for $curr_node" | tee -a $LOG
    echo "-------"
    $TANGLER_CLI -4 -t $curr_node  -A -r $ANYCAST_PREFIX
}

# ----------------------------------------------------------------------------
remove_route_from_node(){
    curr_node=$1
    echo "-------"
    echo "remove announcement from $curr_node" | tee -a $LOG
    echo "-------"
    $TANGLER_CLI -4 -t $curr_node  -w
}
# ----------------------------------------------------------------------------


###############################################################################
### Functions End
###############################################################################
