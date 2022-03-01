#!/usr/bin/env python3
###############################################################################
# Verfploeter CLI (VP-CLI.py)
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
# Thu Jul  4 13:43:19 UTC 2019  Initial version
# Thu Mar 18 14:12:14 UTC 2020  Version 0.9
# Thu Sep 23 17:15:03 UTC 2020  Version 1.0 
# Thu Feb 10 09:47:47 UTC 2022  Version 1.1 
# Wed Feb 16 12:48:24 UTC 2022  Version 1.2 #MP changed
#
###############################################################################
### Python modules
import os
import sys
import re
import pandas as pd
import argparse
import threading
import queue as queue
import time 
from argparse import RawTextHelpFormatter
from os import linesep
import importlib
import logging
import IP2Location
import multiprocessing
import numpy as np
import cursor
from pandarallel import pandarallel

###############################################################################
### Program settings
verbose = False
version = 1.2
program_name = os.path.basename(__file__)
###############################################################################
### Subrotines

#------------------------------------------------------------------------------
def set_log_level(log_level=logging.INFO):
    """Sets the log level of the notebook. Per default this is 'INFO' but
    can be changed.
    :param level: level to be passed to logging (defaults to 'INFO')
    :type level: str
    """
    importlib.reload(logging)
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
    parser.add_argument("-v","--verbose", help="print info msg", action="store_true")
    parser.add_argument("-d","--debug", help="print debug info", action="store_true")
    parser.add_argument("-q","--quiet", help="ignore animation", action="store_true")
    parser.add_argument('-f','--file', nargs='?', help="Verfploeter measurement output file")
    parser.add_argument("-n","--normalize", help="remove inconsistency from the measurement dataset and rebuild geolocation", action="store_true")
    parser.add_argument("-g","--geo",  nargs='+', help="geo-location database - IP2Location (BIN)")
    parser.add_argument("--hitlist",  nargs='+', help="IPv4 hitlist - used to find unknown stats", dest="hitlist")
    parser.add_argument('-s','--source', nargs='?', help="Verfploeter source pinger node to be inserted as metadata")
    parser.add_argument('-b','--bgp', nargs='?', help="BGP policy to be inserted as metadata" )
    parser.add_argument('-w','--weight', nargs='+', help="File used to weight the /24. Use the SIDN load file.")
    parser.add_argument('--filter', action="store_true" , help="Build a new file with the intersection of `weighted` and input file.")
    parser.add_argument("--csv", help="print server load distribution using csv", action="store_true")

    # TODO block and country
#    parser.add_argument("--stats", dest="stats",  choices=["load", "block", "country"], default="",
#	help="show stats from the vp measurement. Potential options:" + linesep +
#	        linesep.join("    " + name for name in ["load (default)", "block", "country"]))
    return parser

#------------------------------------------------------------------------------
# ## remove inconsistency and add metadata field
def check_metadata_from_df(ret,df,args):
  
    # remove inconsistency
    if (args.debug):
        logging.debug("Before removing inconsistency: \"%d\"", len(df))

    # set timestamp as the first transmited packet for the whole measurement
    df['timestamp'] = pd.to_datetime(df['transmit_time'],unit='ns', utc=True)
    df['id'] = df['transmit_time'].min()

    df = df[df['destination_address'] == df['meta_source_address']]
    df = df[df['source_address'] == df['meta_destination_address']]
    df['src_net'] =  df.source_address.str.extract('(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.)\\d{1,3}')+"0"
    df = df.fillna(0)
    df.drop_duplicates(subset="src_net",keep='first', inplace=True)

    # rename columns
    df.rename( columns={'send_receive_time_diff':'rtt',
                        'source_address_country': 'country',
                        'source_address_asn': 'asn',
                        'client_id': 'catchment',
                       }
              ,inplace=True)
    df = df.drop(columns=['source_address','destination_address','meta_source_address',\
                'meta_destination_address','task_id','transmit_time','receive_time'])

    if (args.debug):
        logging.debug("After removing inconsistency: \"%d\"", len(df))
    ret.put(df)

#------------------------------------------------------------------------------
# print loading animation
def animated_loading(flag):

    if (flag == 0 ):
        msg = "loading dataframe     "
        chars = "▁▂▃▄▅▆▇█▇▆▅▄▃▁"
    if (flag == 1 ):
        chars = "◢ ◣ ◤ ◥"
        msg = "removing inconsistency"
    if (flag == 2):
        chars = "▖▘▝▗"
        msg = "inserting metadata    "
    if (flag == 3):
        chars = "▖▘▝▗"
        msg = "finding geo info      "
    if (flag == 4):
        chars = "⣾⣽⣻⢿⡿⣟⣯⣷"
        msg = "saving dataframe      "
    cursor.hide()

    for char in chars:
        sys.stdout.write('\r'+msg+''+char)
        time.sleep(.1)
        sys.stdout.flush()

    sys.stdout.write('\r')
    cursor.show()

#------------------------------------------------------------------------------
# load the dataframe 
def load_df (ret,file):
    logging.debug("loading the dataframe") 
    # df = pd.read_csv(file, sep=",", index_col=False, low_memory=False, skiprows=0, nrows=100)
    df = pd.read_csv(file, sep=",", index_col=False, low_memory=False, skiprows=0)
    ret.put(df)
#------------------------------------------------------------------------------
# add geo info in the dataframe
def ip2location_info(src_net, args,df):
    ip2location = args.ip2location

    rec = ip2location.get_all(src_net)
    country_short = (rec.country_short).decode("utf-8") if rec.country_short else "Unknown"
    region = (rec.region).decode("utf-8") if rec.region else "Unknown"
    lat = rec.latitude if  rec.latitude else 0
    lon = rec.longitude if rec.longitude else 0
    
    result = "{};{};{};{}".format(country_short,region,lat,lon)
    return  (result)

#------------------------------------------------------------------------------
# add geo  - threading
def get_geo_info(params): 

    df = params[0]
    output_file = params[1]
    ip2locationdb = params[2]

    ip2location = IP2Location.IP2Location()
    ip2location.open(ip2locationdb)
    
    # country
    f = lambda x: ip2location.get_country_short(x)
    df['country_ip2location'] = df['src_net'].apply(f)
    df['country_ip2location'] = df['country_ip2location'].str.decode("utf-8").str.replace(",","")
    
    # region
    f = lambda x: ip2location.get_region(x)
    df['region'] = df['src_net'].apply(f)
    df['region'] = df['region'].str.decode("utf-8").str.replace(",","")
    
    f = lambda x: ip2location.get_latitude(x)
    df['latitude'] = df['src_net'].apply(f)
    
    f = lambda x: ip2location.get_longitude(x)
    df['longitude'] = df['src_net'].apply(f)   
    df = df.fillna(0) 
    return ([df, output_file])

def get_ip2loc_data(net):
    ''' Get ip2location data using ip2location functions. Use NET /24 as reference 
        Returns country_short, region, latitude and longitude 
    '''
    # ipv = ip.split(".")
    # ipv[3] = '0'
    # net = '.'.join(ipv)
    ip2location = IP2Location.IP2Location()
    ip2location.open(ip2locationdb)
    
    cc = ip2location.get_country_short(net).replace(",","")
    region = ip2location.get_region(net).replace(",","")
    lat = ip2location.get_latitude(net)
    lon = ip2location.get_longitude(net)
    
    #print (net, cc, region, lat, lon )
    return pd.Series([cc, region, lat, lon])

#------------------------------------------------------------------------------
#
def collect_results(params):

    result = params[0]
    output_file = params[1]

    df_array.append(result)
   
    if not (os.path.isfile(output_file)):
        with open(output_file, 'a') as f:
            result.to_csv(f, header=True)
    else: 
        with open(output_file, 'a') as f:
            result.to_csv(f, header=False)

#------------------------------------------------------------------------------
# plot the graph
def bar(row):
    percent = int(row['percent'])
    bar_chunks, remainder = divmod(int(percent * 8 / increment), 8)
    count = str(row['counts'])
    label = row['site']
    percent = str(percent)

    bar = '█' * bar_chunks
    if remainder > 0:
        bar += chr(ord('█') + (8 - remainder))
    # If the bar is empty, add a left one-eighth block
    bar = bar or  '▏'
    print ("{} | {} - {}%  {}".format( label.rjust(longest_label_length), count.rjust(longest_count_length),percent.rjust(3), bar ))
    return ()

##------------------------------------------------------------------------------
## save df 
#def save_df(df,file):
#
#    outputfile = re.sub('.csv.*', '', args.file)+".csv.norm"
#    df.to_csv(outputfile,index=False, compression="gzip")
#
#    ret.put(outputfile)
#
#------------------------------------------------------------------------------
# load the dataframe and remove inconsistency
def init_load(args):
    logging.info("Starting init_load()")

    file = args.file
    ## load dataframe
    logging.info("reading the dataframe - file {}".format(file)) 
    #logging.debug("reading the dataframe - file {}".format(file)) 
    ret = queue.Queue()
    the_process = threading.Thread(name='process', target=load_df, args=(ret,file))
    the_process.start()
    while the_process.is_alive():
    	animated_loading(0) if not (args.quiet) else 0
    the_process.join()
    df = ret.get()
    
    # not enought lines
    if (df.size<3):
        sys.exit("{} has not enought lines to be processed".format(args.file))
        
    if not 'transmit_time' in df.columns:
        return (df)

    ## check for metadata and pre-processing tasks
    logging.info("checking dataframe metadata")
    ret = queue.Queue()
    the_process = threading.Thread(name='process', target=check_metadata_from_df, args=(ret,df,args))
    the_process.start()
    while the_process.is_alive():
    	animated_loading(1) if not (args.quiet) else 0
    animated_loading(4) if not (args.quiet) else 0
    #print ('\r')

    the_process.join()
    df = ret.get()
    
    logging.info("Returning from init_load()")
    return (df)


#------------------------------------------------------------------------------
# check parameters
def add_weight(filename,df):

    df_load = pd.read_csv(filename,names=['netblock','weight'], index_col=False, low_memory=False, skiprows=0)
    df_load = df_load.sort_values(by='netblock')
    df_aux = pd.merge(df, df_load, left_on='src_net',right_on='netblock',how='left')
    del df_aux['netblock']
    df_aux.fillna('0', inplace=True)
    df_aux['weight'] = df_aux['weight'].astype(int)
    return (df_aux)

#------------------------------------------------------------------------------
# check parameters
def evaluate_args():
    parser = parser_args()
    args = parser.parse_args()

    if (args.debug):
        set_log_level('DEBUG')
        args.quiet=True
        logging.debug(args)

    if (args.version):
        print (version)
        sys.exit(0)
    
    if (args.verbose):
        verbose=True
        set_log_level('INFO')
        args.quiet=True
 
    if (args.csv):
        args.quiet=True

    if (args.geo):
        file = args.geo[0]
        if not (os.path.isfile(file)):
            print ("Geo database file not found: {}".format(file))
            sys.exit(0)

    if (args.filter):
        if not (args.weight):
            print ("You should provide the weight file as well.")
            sys.exit(0)

    if (args.weight):
        file = args.weight[0]
        if not (os.path.isfile(file)):
            print ("Weight file not found: {}".format(file))
            sys.exit(0)

    if (args.file):
        file = args.file
        if not (os.path.isfile(file)):
            print ("file not found: {}".format(file))
            sys.exit(0)
    
    else:
        print ("You have to define the filename")
        parser.print_help()
        sys.exit(0)

    return (args)

###############################################################################
### Main Process

args = evaluate_args()
df_array = []

logging.debug("init")

# load DF
df = init_load(args)

if (args.quiet):
    pandarallel.initialize(verbose=0)
else:
    pandarallel.initialize(progress_bar=True, verbose=1)

# add weight 
if (args.weight):
    logging.debug("Add load based on file {}".format(args.weight[0]))
    file_weight = args.weight[0]
    df = add_weight(file_weight,df)

# add information about geo-location using IP2location
if (args.normalize):

    # add extra metadata info
    # origin = node that has started the ping process
    # bgp = current bgp announces
    df['origin'] = args.source
    df['bgp'] = args.bgp

    ## check for metadata and pre-processing tasks
    logging.info("saving normalized file") 
    
    # geo is not specify dont do anything
    if not (args.geo):
        logging.debug("no geo database provided")
        print ("In file conversion (-n) you must pass the geolocation database")
        sys.exit(1)

    # Changed multiprocessing - linux/macos issues (Leandro)    
    # chunksize = 100
    print ("\rgeolocating the dataframe    ") if not args.quiet else 0
    # pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    logging.info('Starting MP')

    outputfile = re.sub('.csv.*', '', args.file)+".csv.norm"
    ip2locationdb = args.geo[0]
  
    # for df_split in np.array_split(df, chunksize):
    #     result = pool.apply_async(get_geo_info, args=[(df_split,outputfile,ip2locationdb)], callback=collect_results)
    # pool.close()
    # pool.join()

    df[['country_ip2location','region','latitude','longitude']]=df['src_net'].parallel_apply(get_ip2loc_data)
    logging.debug('Done MP')

    # zip file
    logging.debug("saving dataframe ... {} done!".format(outputfile))
    logging.info("saving dataframe ... {} done!".format(outputfile))
    outputfile = re.sub('.csv.*', '', args.file)+".csv.norm.gz"
    print (outputfile)
    df.to_csv(outputfile,index=False, compression="gzip")

elif (args.filter):
    logging.info("Filtering ....")
    df_load = df[df.weight>0]
    outputfile = re.sub('.csv.*', '', args.file)+".csv.load.gz"
    print (outputfile)
    df_load.to_csv(outputfile,index=False, compression="gzip")

## provide load distribution per site
else:
    # new stats df 
    logging.info("Calculating stats...")
    if (args.weight):
        logging.debug("Stats considering the weight")
        df_summary = df[df.weight>0].catchment.value_counts()
    else:
        df_summary = df.catchment.value_counts()

    if (args.hitlist):
        logging.debug ("add infos about unknown data [hitlist - received packages]")
        # total lines in the hitlist
        total_lines_hitlist = len(open(args.hitlist[0]).readlines())
        unknown = (total_lines_hitlist - df.catchment.value_counts().sum())
        df_summary = df_summary.append(pd.Series({'unknown' : unknown}))

    # prepare dataframe 
    df_summary = df_summary.reset_index()
    df_summary.columns = ['site', 'counts']
    df_summary['percent'] = (df_summary['counts']/df_summary['counts'].sum()).mul(100).round(1).astype(int)

    if (args.csv):
        logging.info("Generating CSV stats...")
        print ("#policy,{}".format(args.bgp.replace('"','')))
        print ("#timestamp,{}".format(int(time.time())))
        if (args.hitlist):
            print (f"#hitlist,{args.hitlist}")
        else:
            print ("#hitlist,not_provided")
        if (args.weight):
            print ("#weight assigned")

        header =  (','.join([i for i in df_summary.columns.tolist()]))
        print (header)
        print (df_summary.to_csv(index=False,header=False))

    else:
        logging.info("Generating regular stats...")
        # print ascii bar chart
        max_value = df_summary.percent.max()
        increment = max_value / 25
        longest_label_length = len(df_summary['site'].max())
        longest_count_length = len(df_summary['counts'].max().astype(str))
        ret  = df_summary.apply(bar, axis=1)

if not (args.quiet):
    cursor.show()

logging.info("Done! Exiting...")

sys.exit(0)
