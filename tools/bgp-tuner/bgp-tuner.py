#!/usr/bin/env python
# coding: utf-8

# ## DASHBOARD visualization prototype for SAND/PAADDOS 
# SAND/PAADDOS anycast management Interface (GUI)
# 
# DESCRIPTION:
#     BGP ANYCAST TUNER is a prototype graphical interface that provides a simple 
#     and intuitive interface for operators and presents the distribution of clients 
#     over the anycast sites for the different pre-determined BGP configurations 
#     from the BGP Anycast Playbook.
#     
#     The interface shows the client distribution for each site using a histogram, 
#     and sliders underneath the histogram. 
#     
#     Using these sliders, operators can increase or decrease the catchment of a site 
#     using a set of predetermined settings indicated by “notches” on the slider. 
#     These notches correspond to specific BGP policies, the effect on catchment.
# 
# LIMITATIONS:
#     This version is prepared for anycast sites: CDG, IAD, LHR, MIA, POA, SYD
#     
# REQUIREMENTS:
#     To run this notebook, it's necessary to previously build the anycast playbook
#     For convenience, we provide some BGP playbook samples in the dataset directory.
#     
#     To run the GUI interface first install the python requirements needed and 
#     run SAND-BGP-POLICY-PLAYGROUND.py
# 
#     To access the interface just open your browser on http://127.0.0.1:12345/ 
#     as indicated by the program output.
# 
# USAGE:
#     pip install -r requirements.txt 
#     ./SAND-BGP-POLICY-PLAYGROUND.py
#     
# CONTACT: leandro.bertholdo@gmail.com and ceron@botlog.org
# ---
# ---
# <h1 align="center"> Prepend Policy Graph</h1>
# 
# ---
# ---


import pandas as pd
import numpy as np
from pandas import *

#!pip install -r requirements.txt 


# import plotly.plotly as py
import chart_studio.plotly  as py
import plotly.graph_objs as go
import plotly 
from plotly import exceptions
import plotly.figure_factory as ff
import colorlover as cl
from IPython.display import HTML
from plotly import tools

import plotly.graph_objs as go
import chart_studio.plotly as py
import plotly 

from plotly import exceptions
import plotly.figure_factory as ff


# In[8]:


import dash

from dash import dcc
from dash import html
#import dash_html_components as html


import dash_colorscales
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
# import ipynb.fs.full.SANDparser as sand  

# ###  A) Prepend DF absolute

# prepend_df
# prepend_df = pd.read_csv("prepend-only-dataframe.csv", sep=";")

prepend_df = pd.read_csv("./dataset/prepend+withdraw-dataframe.csv", sep=";")  #### AQUI ####

data = prepend_df
data.drop('HND',1,inplace=True)
data.drop('unknown',1,inplace=True)
# data = data[~data['bgp'].str.contains("-")]
data.head()
data_prepend = data
data_prepend.head(1)
data[data.bgp.str.contains("0x")]
#data[data.bgp.str.contains("-1")]

#data_prepend.head(50)
#data[data.bgp.str.contains("0x")]
#prepend_df.head(100)


#prepend_df[prepend_df.bgp.str.contains("0xCDG")]


# ###  B) Prepend DF percent

# prepend percent
data = pd.read_csv("./dataset/prepend+withdraw-dataframe.csv", sep=";")
data.drop('unknown',1,inplace=True)
data['total'] = prepend_df.sum(axis=1)
df_prepend_percent = pd.DataFrame()
df_prepend_percent['bgp'] = data['bgp']
for node in data.columns[1:8]:
    node_pct = "{}_pct".format(node)
    df_prepend_percent[node] = (data[node]/data['total']).mul(100).round(3)
    
df_prepend_percent.to_csv("./dataset/prepend-only-dataframe_percent.csv", sep=";")
# df_prepend_percent = data2[~data['bgp'].str.contains("-")]
df_prepend_percent.head(1)


data = df_prepend_percent
# get baseline values
data_baseline  = data.iloc[0,1:]
data_baseline
df_prepend_diff = data.iloc[0:,1:].apply(lambda x: (x - data_baseline) , axis=1) 
df_prepend_diff = df_prepend_diff.round(3)
df_prepend_diff['bgp'] = data['bgp']

# # change column order
cols = list(df_prepend_diff.columns)
cols = [cols[-1]] + cols[:-1]
df_prepend_diff = df_prepend_diff[cols]
df_prepend_diff

def build_graph_for_bgp_policy(data,policy="baseline"):    ## AQUI
#def build_graph_for_bgp_policy(data,policy):   


    ## filter dataframe
    df_bgp_policy = data[data['bgp'] == policy].T.reset_index()[1:]
    df_bgp_policy.rename(
        columns={
            df_bgp_policy.columns[1]: "count",
            df_bgp_policy.columns[0]: "site"
        }, inplace = True)
    
    # graph layout
    layout = go.Layout(
        width=590,
        height=250,
        barmode='overlay',
        margin=dict(l=50, r=0, t=20, b=20),
        showlegend=False, 
        
        # Y axis
        yaxis = dict(
         fixedrange = False,
         range = [0,3500000],
         title = "nets (/24)",
         ticksuffix = "",
        ),   
        )
    
    # graph data
    graph_data = dict(
                    type='bar',
                    name = policy,

                    x=df_bgp_policy['site'],
                    y=df_bgp_policy['count'],
                    showlegend=False,
                    hovertext="",
                    hoverinfo = "y",
                    text = df_bgp_policy['count'],
                    marker=dict(color="blue"),
                    customdata = (policy,),
                )
    
    return (go.Figure(data=graph_data, layout=layout))


#policy = "-5xIAD"   
#policy = "-1xIAD" 
policy = "baseline"
fig_server_load = build_graph_for_bgp_policy(data_prepend,policy)
#plotly.offline.iplot(fig_server_load)  ### AQUI ###

data.head()

def build_sliders(data,site):
    
    id = "slider-{}".format(site)
    print (id)
    data = data[~data.bgp.str.contains("0x")]
    marks = dict()
    value_baseline = data.loc[df_prepend_percent.bgp=='baseline',site].values[0]
    marks[-50] = {'label': '-', 'style': {'color': '#000000',"font-size": "14px"}}
    marks[50] = {'label': '+', 'style': {'color': '#000000', "font-size": "14px"}}
    
    # remove not prepended site
    # by convention, "0x" in the policy name means 
    # that the site was disabled


    for value in data[site].sort_values():
        label = " "
        marks[value] = label 
    
    max_value = 50
 
    
    slider =  dcc.Slider(
            id=id,
            min=-50,
            max=max_value,
            step=None,
            vertical="True",
            verticalHeight = "180",
            marks=marks,
            value=value_baseline,
#             tooltip=marks,
            included=False,
        className="range-field w-75") 
#           className="icon glyphicon glyphicon-chevron-left slick-arrow") 

    
    return html.Div([slider])

#slider =  build_sliders(df_prepend_diff,"IAD")   ### AQUI ###

data[data.bgp.str.contains("0x")]

#0x = not prepend but node shutdown
data = data[~data.bgp.str.contains("0x")]

# find the top values
def europe_sum(line):
    return (line['CDG']+line['LHR'])
data['europe'] = data.apply(europe_sum,axis=1)
def eua_sum(line):
    return (line['MIA']+line['IAD'])
data['eua'] = data.apply(eua_sum,axis=1)

policy_max_europe = data.iloc[data.europe.idxmax()]['bgp']
policy_max_eua = data.iloc[data.eua.idxmax()]['bgp']           # AQUI #
#policy_max_eua = '-1xIAD'                                  ###### AQUI ######
policy_max_br = data.iloc[data.POA.idxmax()]['bgp']
policy_max_asia = data.iloc[data.SYD.idxmax()]['bgp']

policy_min_europe = data.iloc[data.europe.idxmin()]['bgp']
policy_min_eua = data.iloc[data.eua.idxmin()]['bgp']
policy_min_br = data.iloc[data.POA.idxmin()]['bgp']
policy_min_asia = data.iloc[data.SYD.idxmin()]['bgp']

# data.iloc[data.CDG.idxmax()]['CDG']

# build label describing the policy selected
def define_label(policy):
    
    header_label = "Site Load Distribution {}".format(policy)
    print (policy)
    if not (policy):
        policy = "baseline"
        header_label = "Site Load Distribution {}".format(policy)
        return (header_label,"")
    
    info_label = policy
    if (policy=="baseline"):
        info_label = "Default Anycast configuration"
    elif "0x" in policy:
        info_label = "Remove prefix announcement for CDG"
        
    elif "-" not in policy:
        info_label = " {} prepend(s) on site {}.".format(policy.split("x")[0],policy.split("x")[1])
    elif "-" in policy:
        nodes = ["CDG","LHR","IAD","SYD","POA", "MIA"]
        nodes.remove(policy.split("x")[1])
        list_nodes = ', '.join([str(elem) for elem in nodes]) 
        num_prepends = policy.split("x")[0].replace("-","")
        info_label = " {} prepend(s) on sites {}.".format(num_prepends,list_nodes)
    
    return (header_label,info_label)

NAVBAR = dbc.Navbar(
    children=[
        html.A(
            dbc.Row(
                [
                    dbc.Col(
                        dbc.NavbarBrand("SAND/PAADDOS Project - The BGP Anycast Playground",
                        className="ml-2")
                    ),
                ],
                align="center",
                #no_gutters=True,  ### AQUI
            ),
            href="http://paaddos.nl/",
        )
    ],
    color="dark",
    dark=True,
    sticky="top",
)

row_sliders = dbc.Col(
        [                                      
        html.Div([
            html.Span("CDG"),
            build_sliders(df_prepend_diff,"CDG"),
        ],className="float-center p-4 border bg-light d-inline-block"),

        html.Div([
            html.Span("IAD"),
            build_sliders(df_prepend_diff,"IAD"),
        ],className="float-center p-4  border bg-light d-inline-block"),

        html.Div([
            html.Span("LHR"),
            build_sliders(df_prepend_diff,"LHR"),
        ],className="float-center p-4  border bg-light d-inline-block"),

        html.Div([
            html.Span("MIA"),
            build_sliders(df_prepend_diff,"MIA"),
        ],className="float-center p-4  border bg-light d-inline-block"),

        html.Div([
            html.Span("POA"),
            build_sliders(df_prepend_diff,"POA"),
        ],className="float-center p-4  border bg-light d-inline-block"),

        html.Div([
            html.Span("SYD"),
            build_sliders(df_prepend_diff,"SYD"),
        ],className="float-center p-4  border bg-light d-inline-block"),

    ],className="ml-2 pl-5",
)

def build_dropdown():
    
   return (dcc.Dropdown(
        id='dropdown', multi=False,clearable=True, style={"marginBottom": 10, "font-size": 12},
        options=[
            {'label': 'Bring traffic to Europe', 'value': policy_max_europe},
            {'label': 'Bring traffic to EUA', 'value': policy_max_eua},
            {'label': 'Bring traffic to South America', 'value': policy_max_br},
            {'label': 'Bring traffic to Asia', 'value': policy_max_asia},
            {'label': 'Get rid of traffic in Europe', 'value': policy_min_europe},
            {'label': 'Get rid of traffic in EUA', 'value': policy_min_eua},
            {'label': 'Get rid of traffic in South America', 'value': policy_min_br},
            {'label': 'Get rid of traffic in Asia', 'value': policy_min_asia},
            {'label': 'Remove node CDG', 'value': "0xCDG"},
            {'label': 'Remove node IAD', 'value': "0xIAD"},
            {'label': 'Remove node LHR', 'value': "0xLHR"},
            {'label': 'Remove node MIA', 'value': "0xMIA"},
            {'label': 'Remove node POA', 'value': "0xPOA"},
            {'label': 'Remove node SYD', 'value': "0xSYD"},
        ],
        placeholder="Select a policy",
        value = "baseline",
        )
    )        
build_dropdown()

def build_modal(value="baseline"):
    
    modal = dbc.Modal([
                dbc.ModalHeader("The following BGP policy will be applied:"),
                dbc.ModalBody(
                    [
#                         html.H5("The following configuation will be applied:"),
                        html.Div(id='modal-content')
                    ]),
        
                dbc.ModalFooter(
                    dbc.Button("Close", id="close", className="ml-auto")
                ),
                
            ],
            id="modal",
            )
    return modal
build_modal()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

LEFT_COLUMN = dbc.Jumbotron(
    [
        dbc.Col(html.Img(src=app.get_asset_url("sand-logo.png"), height="35px",
         className="mr-4 pr-2")),
        
        html.H6("Select desired goal", style={"marginTop": 50}, className="lead"),
        html.P(
            "(You can use the dropdown and see the load change on the graph.)",
            style={"fontSize": 10, "font-weight": "lighter"},
        ),
        build_dropdown(),
        html.Div(
            dbc.Button("Deploy", color="success", block=True, id="button")
        ),
        
        # store value 
        html.Div(id='bgp-value', style={'display': 'none'}),
        build_modal()
    ],
)


toast = dbc.Toast(
                    [
                        html.P("This is the default configuration", id="policy-description", className="mb-0")
                    ],
                    header="BGP Policy Description",
                    is_open=True,
                    dismissable=True,
                    icon="danger",                
                )

card_content = [ 
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader("Site Load Distribution",id="policy-description-header"),
                        dbc.CardBody(
                        [
                            dcc.Graph(id="serve-load-graph",figure=fig_server_load,
                            config={'displayModeBar': False}),
                            row_sliders, 
                        ]
                        ),
                    ],color="white"
                )
            )
]


BODY = dbc.Container(
    [
        dbc.Row(
            [
              dbc.Col(LEFT_COLUMN, md=3, align="top",width={"size": 0, "offset": 0}),

              dbc.Col(dbc.Container(
                [   
                    dbc.Row(card_content),
                ],style={"padding": "0px 0px 00px 0px"}), md=8),              
            ],
        
        ),
        dbc.Row(dbc.Col([toast],style={"padding": "0px 0px 20px 0px"}, md=3))
    ],
    className="p-3",
)

# source_node = "CDG"
# string_regex = "0x{}".format(source_node)
# df_prepend_diff = df_prepend_diff[['bgp', 'IAD', 'LHR', 'MIA', 'POA', 'SYD']]
# df_prepend_diff[df_prepend_diff.bgp.str.contains(string_regex)].iloc[0,1:]

#df_aux = df_prepend_diff[['bgp', 'IAD', 'LHR', 'MIA', 'POA', 'SYD']]
#df_aux[df_aux.bgp.str.contains("0xCDG")].iloc[0,1:].tolist()



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div(children=[NAVBAR, BODY])


#### callback for slider CDG 
@app.callback(
    [
     Output("slider-CDG", "value"),
     Output("slider-IAD", "value"),
     Output("slider-LHR", "value"),
     Output("slider-MIA", "value"),
     Output("slider-POA", "value"),
     Output("slider-SYD", "value"),
     Output("serve-load-graph", "figure"),
     Output("policy-description-header", "children"),
     Output("policy-description", "children"),
     Output("modal-content", "children"),
    ],
    [
     Input('slider-CDG', 'value'),
     Input('slider-IAD', 'value'),
     Input("slider-LHR", "value"),
     Input("slider-MIA", "value"),
     Input("slider-POA", "value"),
     Input("slider-SYD", "value"),
     Input('dropdown', 'value'),
    ],
)
def callback_function(value_CDG,value_IAD,value_LHR,value_MIA,value_POA,value_SYD, dropdown_value): 
    #source_node = "CDG"
    results = []
    #nodes = ['IAD', 'LHR', 'MIA', 'POA', 'SYD']
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]


    print("Context: {}".format(ctx.triggered))
    print("Triggred: {}".format(ctx.triggered[0]['prop_id'].split('.')[0]))
    if (trigger == 'slider-CDG'):
        print("Triggered by CDG")
        value = value_CDG
        source_node = "CDG"
    elif (trigger == 'slider-IAD'):
        print("Triggered by IAD")
        value = value_IAD
        source_node = "IAD"
    elif (trigger == 'slider-LHR'):
        print("Triggered by LHR")
        value = value_LHR
        source_node = "LHR"
    elif (trigger == 'slider-MIA'):
        print("Triggered by MIA")
        value = value_MIA
        source_node = "MIA"
    elif (trigger == 'slider-POA'):
        print("Triggered by POA")
        value = value_POA
        source_node = "POA"
    elif (trigger == 'slider-SYD'):
        print("Triggered by SYD")
        value = value_SYD
        source_node = "SYD"
    else:
        value = value_CDG
    
    nodes = ['CDG', 'IAD', 'LHR', 'MIA', 'POA', 'SYD']
    #nodes.remove(source_node)

    #print(my_input.value)
#     print ("search for {}".format(value))
    
    # means that is not a bgp prepend but node withdraw
    max_slider_value = 50
    min_slider_value = -50
    if (value==min_slider_value):
        print ("remove node {}".format(source_node))
        string_regex = "0x{}".format(source_node)
        policy = string_regex
        lista = ['bgp', 'CDG', 'IAD', 'LHR', 'MIA', 'POA', 'SYD']
        #lista.remove(source_node)
        df_aux = df_prepend_diff[lista]
        #df_aux = df_prepend_diff[['bgp', 'IAD', 'LHR', 'MIA', 'POA', 'SYD']]
        results = df_aux[df_aux.bgp.str.contains(string_regex)].iloc[0,1:].tolist()
        
    else:
        # force max value (50) to be rewrited to the max available value
        if (value==max_slider_value):
            value = df_prepend_diff.iloc[df_prepend_diff[source_node].idxmax()][source_node].tolist()
            print("Valor ", value)
        for node in nodes:
            try:
                new_value = df_prepend_diff.loc[df_prepend_diff[source_node]==value,[node]].values[0][0]
                print('new_value',new_value)
            except:
                print ("this value has not found on diff, so this is the maximum")
                new_value = 0

            results.append(new_value)
        try:  
            policy = df_prepend_diff.loc[df_prepend_diff[source_node]==value,'bgp'].values[0]
        except:
            policy = 0

    if (trigger == 'dropdown'):
        new_value = (df_prepend_diff.loc[df_prepend_diff.bgp==policy,'CDG'].values[0])

    # new figure 
    if (policy):
        fig = build_graph_for_bgp_policy(data_prepend,policy)
    else:
        fig = build_graph_for_bgp_policy(data_prepend)
    results.append(fig)
   
    (label_header, label_info) = define_label(policy)
    
    results.append(label_header) 
    results.append("Policy: "+label_info) 
    results.append(label_info) 

    print("Resultado",results)
    return (results)


#### callback for dropdown
""" @app.callback(
    [
     Output("slider-CDG", "value"),
    ],
    [Input('dropdown', 'value')],
)
def callback_function(policy): 
    try:
        new_value = (df_prepend_diff.loc[df_prepend_diff.bgp==policy,'CDG'].values[0])
    except:
        new_value = "baseline"
    return ([new_value]) """

#### callback for button
@app.callback(
    Output("modal", "is_open"),
    [Input("button", "n_clicks"), 
     Input("close", "n_clicks")],
    [State("modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

if __name__ == '__main__':
    app.run_server(debug=False, port=12345)
