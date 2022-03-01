###############################################################################
#  Configuration file for paaddos/sand scripts
#  Fri Jan 31 18:29:26 CET 2020
#  @copyright ant.isi.edu/paaddos - Leandro Bertholdo - l.m.bertholdo@utwente.nl
###############################################################################
### Program settings
RETVAL=""  #define to global return of verfploeter (dont change)

###############################################################################
### Path configuration
# base execution dir (untar place)
EXECDIR="$HOME/work/catchment_manipulation"

# verfploter configs
VP_BIN="$HOME/.cargo/bin/verfploeter"

# hitlist
HITLIST="$EXECDIR/tools/hitlist.txt"

# geolocation databases
ASN_DB="$EXECDIR/tools/GeoLite2-ASN.mmdb"
GEO_DB="$EXECDIR/tools/GeoLite2-Country.mmdb"
IP2LOCATION="$EXECDIR/tools/IP2LOCATION-LITE-DB9.BIN"

# Tangler-cli
TANGLER_CLI="$EXECDIR/tools/tangler-cli.py -4"

# vp-cli 
VPCLI="$EXECDIR/tools/vp-cli.py"

###############################################################################
# Anycast configuration
# defaults
ANYCAST_ADDRESS="145.100.118.1"
ANYCAST_PREFIX="145.100.118.0/23"
PINGER="us-mia-anycast01"

###############################################################################
### Dataset repository and Logs configuration
# Timestaps
DATE_PARAM="-u +%Y-%m-%d-%Hh%Mm"
DATE_VAR=`date $DATE_PARAM`

# Dataset and Logs
REPO="$EXECDIR/dataset/$DATE_VAR"
LOG="$REPO/log.txt"

###############################################################################
### Routing setups
# time to wait between routing setup and start measuring
# 600s=conservative 300s=good  60s=testing
SLEEP=600

# default name for BGP policy - to be reset on scripts
BGP="non"

###############################################################################
### Tangled Testbed Configs for scripts
# IP for peer routing BIRD on IXPS (Tangled testbed)
BIRD="145.100.119.1"

# Anycast nodes available (Do not afffect tangler-cli.py and run_playbook.py)
# nodes names need to be resolved by DNS
# example: nl-ams-anycast01 to nl-ams-anycast01.node.anycast-testbed.com
declare -a NODES
NODES+=("au-syd-anycast01")
NODES+=("br-gru-anycast01")
NODES+=("br-poa-anycast02")
NODES+=("fr-par-anycast01")
NODES+=("uk-lnd-anycast02")
NODES+=("us-sea-anycast01")  
NODES+=("us-los-anycast01")
NODES+=("us-mia-anycast01")
NODES+=("us-was-anycast01")
NODES+=("de-fra-anycast01")  
NODES+=("sg-sin-anycast01")  
NODES+=("dk-cop-anycast01")
NODES+=("za-jnb-anycast01") 
NODES+=("nl-ens-anycast02")
NODES+=("nl-ams-anycast01") 
NODES+=("nl-arn-anycast01")

### HEFICED_nodes
declare -a IXP_HEFICED
IXP_HEFICED+=("za-jnb-anycast01")  # NAPAfrica

### VULTR_nodes
declare -a IXP_VULTR
IXP_VULTR+=("nl-ams-anycast01")  #IX-AMS
IXP_VULTR+=("au-syd-anycast01")  #IX-AU
IXP_VULTR+=("fr-par-anycast01")  #France-IX
IXP_VULTR+=("uk-lnd-anycast02")  #LINX
IXP_VULTR+=("de-fra-anycast01")  #DEC-IX
IXP_VULTR+=("us-sea-anycast01")  #SIX
IXP_VULTR+=("sg-sin-anycast01")  #EQ-IX

### Direct IXPs using Bird
declare -a IXP_DIRECT
IXP_DIRECT+=("br-gru-anycast01")  #IX-GRU
IXP_DIRECT+=("br-poa-anycast02")  #IX-POA

### BGP Communities VULTR_nodes
declare -a VCOMM
#VCOMM+=("20473:6601")   #no-ix just VULTR private peering
#VCOMM+=("64600:6000")   #no-export
#VCOMM+=("64600:63956")  #no-ix-au
VCOMM+=("64600:2914")    #no-ntt
VCOMM+=("64600:1299")    #no-telia
VCOMM+=("64600:3257")    #no-gtt
VCOMM+=("64600:3356")    #no-centurylink
VCOMM+=("64600:174")     #no-cogent
VCOMM+=("64600:7922")    #no-comcast
VCOMM+=("64600:63956")   #no-equinix-AU
VCOMM+=("64600:3491")    #no-PCCW Singapure
VCOMM+=("64600:2516")    #no-KDDI Tokyo 
VCOMM+=("64600:9318")    #no-SKB South-Corea KINX
VCOMM+=("0:1103")        #no surfnet on AMSIX
VCOMM+=("0:2603")        #no nordunet on AMSIX
VCOMM+=("64600:2603")    #no nordunet on VULTR private peering

### BGP Communities HEFICED_nodes
declare -a HCOMM
HCOMM+=("61317:65100")   #no-telia
HCOMM+=("61317:65110")   #no-gtt
HCOMM+=("61317:65120")   #no-pccw
HCOMM+=("61317:65130")   #no-ntt
HCOMM+=("61317:65140")   #no-centurylink
HCOMM+=("61317:65150")   #no-servercentral
HCOMM+=("61317:65160")   #no-sparkle
HCOMM+=("61317:65170")   #no-liquid
HCOMM+=("61317:65180")   #no-wiocc
HCOMM+=("61317:65190")   #no-DECIX-Frankfurt
HCOMM+=("61317:65200")   #no-DECIX-Dusseldorf
HCOMM+=("61317:65210")   #no-IX.br
#HCOMM+=("61317:65230")   #no-NAPAfrica
HCOMM+=("61317:65230")   #no-JINX

### BGP Communities IX.br
declare -a BRCOMM
BRCOMM+=("65000:1251")   #no-ansp
BRCOMM+=("65000:20080")  #no-ampath
BRCOMM+=("65000:264575") #Nexfibra
BRCOMM+=("65000:262605") #i7provider.com.br

### END OF CONFIGS
###############################################################################
