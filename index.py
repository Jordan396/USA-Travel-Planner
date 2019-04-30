# Basic imports
import boto3
import datetime
import openpyxl
import time
import random
import base64
import pickle
import ast
import copy
from haversine import haversine
import os

# Data analysis/viz imports
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import networkx as nx
import plotly.graph_objs as go
import plotly.plotly as py

# Web app imports
import json
import requests
from flask import Flask
from flask import send_from_directory
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash
import dash_auth
"""
# External scripts imports
import config

# TODO: REPLACE BELOW API KEYS WITH YOUR OWN
AWS_SECRET_ACCESS_KEY = config.AWS_SECRET_ACCESS_KEY
AWS_ACCESS_KEY_ID = config.AWS_ACCESS_KEY_ID
AWS_REGION_NAME = config.AWS_REGION_NAME
GOOGLE_MAPS_API_KEY = config.GOOGLE_MAPS_API_KEY
"""

AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_REGION_NAME = os.environ['AWS_REGION_NAME']
GOOGLE_MAPS_API_KEY = os.environ['GOOGLE_MAPS_API_KEY']

# Instantiate clients
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


# ===============================================================================================================================
# Web Framework
# ===============================================================================================================================


server = Flask(__name__)

app = dash.Dash('auth', server=server, url_base_pathname='/travelplanner/')
app.title = "USA Travel Planner"

app.config.suppress_callback_exceptions = True

# Scripts and css served locally for faster response time
# app.scripts.config.serve_locally = True is used as it takes a long time to download plotly.js from CDN
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True
					 

# ===============================================================================================================================
# Logic
# ===============================================================================================================================


def state_dropdown():
    states = ['Alabama', 'Alaska', 'Arizona','Arkansas', 'California', 'Colorado','Connecticut', 'Delaware', 'Florida','Georgia', 'Hawaii', 'Idaho','Illinois', 'Indiana', 'Iowa',
    		'Kansas', 'Kentucky', 'Louisiana','Maine', 'Maryland', 'Massachusetts','Michigan', 'Minnesota', 'Mississippi','Missouri', 'Montana', 'Nebraska','Nevada', 'New Hampshire', 
    		'New Jersey', 'New Mexico', 'New York', 'North Carolina','North Dakota', 'Ohio', 'Oklahoma','Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 
    		'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming']

    dropdown_list = []
    for item in states:
        line = {'label': item, 'value': item}
        dropdown_list.append(line)
    return(dropdown_list)


def locate_property(state_value, city_value, property_value,):
  # Find place location
  address = state_value + " " + city_value + " " + property_value
  url = "https://maps.googleapis.com/maps/api/place/textsearch/json?query={}&key={}".format(address, GOOGLE_MAPS_API_KEY)
  req = requests.get(url)
  data = req.json()
  try:
    print(str(data))
    list_loc = data['results']
    property_name = list_loc[0]['name']
    property_loc = (list_loc[0]['geometry']['location']['lat'], list_loc[0]['geometry']['location']['lng'])
    print ("Properties found!")
    print(list_loc)
    print("Selecting first property: "+str(property_name))
    return(property_name, property_loc)
  except:
    return ("Error", (0,0))


def locate_nearby_attractions(property_loc, attractions_value, duration_value):
	# Find nearby attractions
	if (len(attractions_value)==0 or property_loc==(0,0)):
		return ([])
	else:
		radius = 10000
		POIs = []
		for attraction in attractions_value:
			url2 = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={},{}&radius={}&type={}&key={}&rankby=prominence&language=en".format(property_loc[0], property_loc[1], radius, attraction, GOOGLE_MAPS_API_KEY)
			print("Sending request to: "+url2)
			req2 = requests.get(url2)
			data2 = req2.json()
			list_near_by = data2['results']
			for near_by in list_near_by:
				attraction_name = near_by['name']
				attraction_loc = (near_by['geometry']['location']['lat'], near_by['geometry']['location']['lng'])
				POIs.append([attraction_name.title(), attraction_loc, attraction])
		print("Nearby attractions found!")
		print(POIs)
		return (POIs)


def cluster_attractions(POIs, duration_value):
	length_POI = len(POIs)
	if length_POI == 0:
		return ([0])
	elif length_POI <= duration_value:
		location_array = []
		for attraction in POIs:
			location_array.append([attraction[1][0],attraction[1][1]])
		X = np.array(location_array)
		location_df = pd.DataFrame(X, columns=["lat","long"])
		fig = plt.figure(figsize=(8, 6))
		location_df.plot(x="lat",y="long",kind="scatter", title='Coordinates of Locations')
		fig.savefig('/tmp/scatterplot.png', dpi=fig.dpi)

		responseList = [length_POI]
		for attraction in POIs:
			responseList.append([attraction])
		return (responseList)
	else:
		location_array = []
		for attraction in POIs:
			location_array.append([attraction[1][0],attraction[1][1]])
		X = np.array(location_array)
		kmeans = KMeans(n_clusters=duration_value, random_state=0).fit(X)
		labels = kmeans.labels_

		fig = plt.figure(figsize=(8, 6))
		plt.ylabel('Long')
		plt.xlabel('Lat')
		plt.title('Coordinates of Locations')
		plt.scatter(X[:,0], X[:,1], c=kmeans.labels_.astype(float))
		fig.savefig('/tmp/scatterplot.png', dpi=fig.dpi)

		responseList = [duration_value]
		for i in range(1, duration_value+1):
			responseList.append([])
		for idx, value in enumerate(POIs,0):
			responseList[labels[idx]+1].append(value)
		return (responseList)


def get_display(idx, row, attractionTypeDic, outputNumber):

    attraction = row['Attraction']
    location = str(row['Location'])
    attraction_type = attractionTypeDic[row['Type']]
    # score = row['score']

    output = (html.Div(
        [
            html.P([attraction], className='ad-headline123'),
            html.P([attraction_type], className='ad-description123'),
            html.P([location], className='ad-description123'),

            dcc.Checklist(
                options=[
                    {'label': '', 'value': 'selected'}
                ],
                values=[],
                labelStyle={'display': 'inline-block'},
                id='adboxCheckbox'+str(outputNumber)+"-"+str(idx)
            )
            # html.P(["%.2f" % score],)
        ], id='adbox'+str(outputNumber)+"-"+str(idx), className='col-md-4 adbox'),)
    return output


def display_output(df, outputNumber):
	attractionTypeDic = {'amusement_park':'Amusement Park',
					 'aquarium':'Aquarium',
					 'art_gallery':'Art Gallery',
					 'museum':'Museum',
					 'casino':'Casino',
					 'church':'Church',
					 'city_hall':'City Hall',
					 'hindu_temple':'Temple',
					 'mosque':'Mosque',
					 'library':'Library',
					 'park':'Park',
					 'shopping_mall':'Shopping mall',
					 'stadium':'Stadium',
					 'zoo':'Zoo'}
	display = []
	for idx, i in df.iterrows():
		display.extend(get_display(idx, i, attractionTypeDic, outputNumber))
	return(display)


def generate_excel_file(generated_ads_list):

    report_template_file_name = 'reports/Report-Template.xlsx'

    s3 = boto3.client('s3', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    workbook = openpyxl.load_workbook(filename='{}'.format(report_template_file_name))
    sheet = workbook['Report-Template']

    DAY_COL = 'A'
    START_COL = 'B'
    END_COL = 'C'
    DISTANCE_COL = 'D'

    for row, ad in enumerate(generated_ads_list):
        day_cell = DAY_COL + str(row + 2)
        start_cell = START_COL + str(row + 2)
        end_cell = END_COL + str(row + 2)
        distance_cell = DISTANCE_COL + str(row + 2)

        sheet[day_cell].value = ad['Day']
        sheet[start_cell].value = ad['Start']
        sheet[end_cell].value = ad['End']
        sheet[distance_cell].value = ad['Distance']

    time_stamp = datetime.datetime.fromtimestamp(time.time()).strftime('%d-%m-%Y-%H-%M')
    result_file_name = 'reports/' + time_stamp + '-results.xlsx'

    workbook.save(result_file_name)
    s3.upload_file(result_file_name, 'travel-planner', 'generated_results/' + result_file_name)
    download_url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': 'travel-planner',
            'Key': 'generated_results/' + result_file_name
        },
        ExpiresIn=3600
    )
    return download_url


def identifyNodesEdges(locationsList, propertyNode):
    if(len(locationsList)==0):
        return ([])
    else:
        extendedLocationsList = copy.deepcopy(locationsList)
        extendedLocationsList.append(propertyNode)

        complete_dict = {}
        for currentItem in extendedLocationsList:
            for otherItem in extendedLocationsList:
                if (currentItem != otherItem):
                    if currentItem[0] not in complete_dict:
                        complete_dict[currentItem[0]] = [[otherItem[0],haversine(currentItem[1], otherItem[1])]]
                    else:
                        complete_dict[currentItem[0]].append([otherItem[0],haversine(currentItem[1], otherItem[1])])

        visitedNodes_dict = {}
        for key in complete_dict:
            visitedNodes_dict[key]=[key]

        counter_dict = {}
        for key in complete_dict:
            counter_dict[key] = 2

        edgeList = []

        while True:
            try:
                minimum_dict = {}
                for key in complete_dict:
                    distances = []
                    for value in complete_dict[key]:
                        distances.append(value[1])
                    indexOfSmallest = np.argmin(distances)
                    minimum_dict[key]=complete_dict[key][indexOfSmallest]

                shortestDistances=[]
                for key,value in minimum_dict.items():
                    shortestDistances.append(value[1])
                shortestDistance = min(shortestDistances)

                checkIfValidConnection = []
                for key,value in minimum_dict.items():
                    if value[1]==shortestDistance:
                        checkIfValidConnection.append(value[0])

                finalConnection=checkIfValidConnection
                finalConnectionDistance=shortestDistance

                if checkIfValidConnection[1] in visitedNodes_dict[checkIfValidConnection[0]]:
                    # Connecting these 2 nodes forms a cyclic graph
                    filteredList=copy.deepcopy([item for item in complete_dict[checkIfValidConnection[1]] if item[0]!=checkIfValidConnection[0]])
                    complete_dict[checkIfValidConnection[1]]=filteredList
                    filteredList=copy.deepcopy([item for item in complete_dict[checkIfValidConnection[0]] if item[0]!=checkIfValidConnection[1]])
                    complete_dict[checkIfValidConnection[0]]=filteredList
                else:
                    connectedNodes = []
                    for key,value in minimum_dict.items():
                        if value[1]==shortestDistance:
                            connectedNodes.append(value[0])

                            newValue = copy.deepcopy(complete_dict[key])
                            newValue.remove(value)
                            complete_dict[key] = newValue
                            counter_dict[key]=counter_dict[key]-1

                    keysToPop = []
                    for key in counter_dict:  
                        if counter_dict[key]==0:
                            complete_dict.pop(key, None)
                            keysToPop.append(key)
                            for completeKey, completeValue in complete_dict.items():
                                filteredList=copy.deepcopy([item for item in completeValue if item[0]!=key])
                                complete_dict[completeKey]=filteredList

                    for key in keysToPop:
                        counter_dict.pop(key, None)
                    for node in visitedNodes_dict[connectedNodes[0]]:
                        visitedNodes_dict[node]=visitedNodes_dict[node]+list(set(visitedNodes_dict[connectedNodes[1]])-set(visitedNodes_dict[node]))
                    for node in visitedNodes_dict[connectedNodes[1]]:
                        visitedNodes_dict[node]=visitedNodes_dict[node]+list(set(visitedNodes_dict[connectedNodes[0]])-set(visitedNodes_dict[node]))    

                    edgeList.append([tuple(connectedNodes),shortestDistance])
            except:
                break
        edgeList.append([tuple(finalConnection),finalConnectionDistance])
        return(edgeList)


def constructGraph(masterGraph):
    masterGraph=json.loads(masterGraph)
    G=nx.Graph()

    for node in masterGraph[-2]:
        G.add_node(node[0])
    G.add_node(masterGraph[-1][0])

    for dayList in masterGraph[:-2]:
        if len(dayList)!=0:
            for edge in dayList:
                G.add_edge(edge[0][0], edge[0][1], weight=round(edge[1],4))

    plt.figure(figsize=(15,10))
    plt.title('Shortest Route For Each Day')
    pos = nx.spring_layout(G)
    labels = nx.get_edge_attributes(G,'weight')
    nx.draw_networkx(G,pos,node_size=10,node_color='g', font_size=11)
    nx.draw_networkx_edge_labels(G,pos,edge_labels=labels)
    plt.savefig("/tmp/graphnetwork.png", format="PNG")


# ===============================================================================================================================
# View
# ===============================================================================================================================


app.layout = html.Div(children=[
    # Adding stylesheet referenes here as app.css.config.serve_locally = True
    # app.css.config.serve_locally = True is used as it takes a long time to download plotly.js from CDN
    # So cannot add in external stylesheets
    # Have to wait for plotly to release an update to fix this issue
    html.Link(
        rel='stylesheet',
        href='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css'
    ),

    html.Link(
        rel='stylesheet',
        # href='assets/dash-stylesheet.css'
        href='https://s3.ap-southeast-1.amazonaws.com/travel-planner/stylesheets/dash-stylesheet.css'
    ),

    html.H2(children='USA Travel Planner', style={'text-align': 'center',
                                           'border-radius': '25px',
                                           'padding-bottom': '30px',
                                           'padding-top': '30px'}),

    html.Hr(),
    
    html.Details([
        html.Summary('Where would you like to go?',style={'font-weight': 'bold'}),
        html.Br(),
        html.Div([
            # contains the text box for user inputs
            html.Div([

                html.P([
                    html.Label('STATE'),
                    dcc.Dropdown(
                        id='state_box',
                        options=state_dropdown(),
                        value='')], style={'width': '570px', 'padding-bottom': '15px', 'margin': 'auto'}
                       ),

                html.P([
                    html.Label('CITY'),
                    dcc.Dropdown(
                        id='city_box',
                        options="",
                        value='')], style={'width': '570px', 'padding-bottom': '15px', 'margin': 'auto'}
                       ),

                html.P([
                    html.Label('ATTRACTIONS'),
                    dcc.Dropdown(
                    	id = 'attractions_dropdown',
						options=[
							{'label': 'Amusement Park', 'value': 'amusement_park'},
							{'label': 'Aquarium', 'value': 'aquarium'},
							{'label': 'Art Gallery', 'value': 'art_gallery'},
							{'label': 'Museum', 'value': 'museum'},
							{'label': 'Casino', 'value': 'casino'},
							{'label': 'Church', 'value': 'church'},
							{'label': 'City Hall', 'value': 'city_hall'},
							{'label': 'Temple', 'value': 'hindu_temple'},
							{'label': 'Mosque', 'value': 'mosque'},
							{'label': 'Library', 'value': 'library'},
							{'label': 'Park', 'value': 'park'},
							{'label': 'Shopping mall', 'value': 'shopping_mall'},
							{'label': 'Stadium', 'value': 'stadium'},
							{'label': 'Zoo', 'value': 'zoo'}
						],
						value=[],
						multi=True
						)], style={'width': '570px', 'padding-bottom': '15px', 'margin': 'auto'}
                    ),

                html.P([
                    html.Label("ACCOMMODATION"),
                    html.Br(),
                    dcc.Input(
                    	id = 'property_text',
					    placeholder='Where will you be staying? If unknown, leave as blank.',
					    type='text',
					    value='',
					    style={'width': '100%'})], style={'width': '570px', 'padding-bottom': '20px', 'margin': 'auto'}
                       ),


                html.P([
                    html.Label('DURATION OF STAY'),
                    dcc.Slider(
                    	id = 'duration_slider',
					    min=1,
					    max=7,
					    marks={1: '1 day', 2: '2 days', 3: '3 days', 4: '4 days', 5: '5 days', 6: '6 days', 7: '7 days'},
					    value=1)], style={'width': '570px', 'padding-bottom': '15px', 'margin': 'auto'}
                       )
            ], style={'margin-bottom': '20px', 'text-align': 'center'}),
            html.Button(id='submit-button-one', n_clicks=0, n_clicks_timestamp='0', children='Proceed', className="btn btn-success", style={'width': '10%'})
        ])
    ], id='step-1-details', open=True),

    html.Hr(),

    html.Details([
        html.Summary('Just a little more planning...',style={'font-weight': 'bold'}),
        html.Br(),
        html.Img(id='plotImage', src=''),
        html.Br(),
        html.H2('For each day, select the places you would like to visit'),
        html.Div([html.H2('Day One'),html.Div(id='outputDayOne', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDayOne'),
        html.Div([html.H2('Day Two'),html.Div(id='outputDayTwo', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDayTwo'),
        html.Div([html.H2('Day Three'),html.Div(id='outputDayThree', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDayThree'),
        html.Div([html.H2('Day Four'),html.Div(id='outputDayFour', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDayFour'),
        html.Div([html.H2('Day Five'),html.Div(id='outputDayFive', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDayFive'),
        html.Div([html.H2('Day Six'),html.Div(id='outputDaySix', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDaySix'),
        html.Div([html.H2('Day Seven'),html.Div(id='outputDaySeven', className='row', children=None)], className='container', style={'display': 'none'}, id='segmentDaySeven'),
        html.Br(),
        html.Button(id='submit-button-two', n_clicks=0, n_clicks_timestamp='0', children='Select', className="btn btn-success", style={'width': '10%'})
    ], id='step-2-details', open=False, style={'width':'75%', 'margin': 'auto'}),

    html.Hr(),

    html.Details([
        html.Summary("Let's kick off the adventure! :)",style={'font-weight': 'bold'}),
        html.Img(id='graphImage', src=''),
        html.Br(),
        html.A(html.Button(n_clicks=0, children='Download', className="btn btn-success", style={'width': '10%', 'margin-top': '10px'}), target="_blank", id='download_excel_button')
    ],id='step-3-details', open=False),

    html.Hr(),

    # Hidden div inside the app that stores the intermediate value
    html.Div(id='api_base_response',children=None, style={'display': 'none'}),
    html.Div(id='graph_api_response',children=None, style={'display': 'none'}),
    html.Div(style={'padding-bottom': '200px'})
], style={'padding-left': '10px'}, className="body")


# ===============================================================================================================================
# Control
# ===============================================================================================================================

# =============================
# Controls which step to open
# =============================

@app.callback(Output('step-1-details', 'open'), [Input('submit-button-one', 'n_clicks')])
def openclose_step_one(n_clicks):
    if (n_clicks):
        return False
    else:
        return True

@app.callback(Output('step-2-details', 'open'), [Input('submit-button-one', 'n_clicks'), Input('submit-button-two', 'n_clicks')], 
	[State('submit-button-one', 'n_clicks_timestamp'), State('submit-button-two', 'n_clicks_timestamp')])
def openclose_step_two(buttonOneClicks,buttonTwoClicks, buttonOneTimestamp, buttonTwoTimestamp):
    if (int(buttonOneTimestamp)>int(buttonTwoTimestamp)):
    	time.sleep(6)
    	return True
    else:
    	return False

@app.callback(Output('step-3-details', 'open'), [Input('submit-button-two', 'n_clicks')])
def openclose_step_three(n_clicks):
    if (n_clicks):
    	time.sleep(6)
    	return True
    else:
    	return False

@app.callback(Output('api_base_response', 'children'), [Input('submit-button-one', 'n_clicks')], 
	[State('state_box', 'value'), State('city_box', 'value'), State('attractions_dropdown', 'value'), State('property_text', 'value'), State('duration_slider', 'value')])
def attraction_identifier(n_clicks, state_value, city_value, attractions_value, property_value, duration_value):
    if (n_clicks):
      print("Step one parameters received: "+state_value + " " + city_value + " " + str(attractions_value) + " " + property_value + " " + str(duration_value))
      property_name,property_loc = locate_property(state_value, city_value, property_value)
      print(str(property_name))
      POIs = locate_nearby_attractions(property_loc, attractions_value, duration_value)
      clusteredPOIsResponse = cluster_attractions(POIs, duration_value)
      time.sleep(2)
      print("===================================================================================")
      print("Clustered response: ")
      clusteredPOIsResponse.append([property_name,property_loc])
      print(clusteredPOIsResponse)
      return (json.dumps(clusteredPOIsResponse))
    else:
        return None

@app.callback(Output('plotImage', 'src'), [Input('api_base_response', 'children')])
def updatePlot(api_response):
	print("Change in response detected")
	if (api_response is None):
		print("Serving emptyplot image")
		image_filename = 'img/emptyplot.png'
		encoded_image = base64.b64encode(open(image_filename, 'rb').read())
		return ('data:image/png;base64,{}'.format(encoded_image.decode()))
	else:
		api_response = json.loads(api_response)
		if (api_response[0]==0):
			print("Serving emptyplot image")
			image_filename = 'img/emptyplot.png'
			encoded_image = base64.b64encode(open(image_filename, 'rb').read())
			return ('data:image/png;base64,{}'.format(encoded_image.decode()))
		else:
			print("Serving scatterplot image")
			image_filename = '/tmp/scatterplot.png'
			encoded_image = base64.b64encode(open(image_filename, 'rb').read())
			return ('data:image/png;base64,{}'.format(encoded_image.decode()))

@app.callback(Output('city_box', 'options'), [Input('state_box', 'value')])
def updateCitiesList(value):
	if value == '':
		return None
	else:
		databaseResponse = dynamodb.get_item(TableName='United_States_Cities', Key={'state': {'S': value}},)
		citiesList = databaseResponse['Item']['city']['SS']
		
		dropdown_list = []
		for item in citiesList:
			line = {'label': item, 'value': item}
			dropdown_list.append(line)
		return dropdown_list

@app.callback(Output('graph_api_response', 'children'), [Input('submit-button-two', 'n_clicks')], [State('step-2-details', 'children'), State('api_base_response', 'children')])
def determineGraphPoints(n_clicks, details, api_base_response):
	if n_clicks:
		dayOneList=[]
		dayTwoList=[]
		dayThreeList=[]
		dayFourList=[]
		dayFiveList=[]
		daySixList=[]
		daySevenList=[]

		for child in details:
			try:
				if child['props']['id']=="segmentDayOne":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							dayOneList.append([childElements[0]['props']['children'][0], location])

				if child['props']['id']=="segmentDayTwo":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							dayTwoList.append([childElements[0]['props']['children'][0], location])

				if child['props']['id']=="segmentDayThree":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							dayThreeList.append([childElements[0]['props']['children'][0], location])

				if child['props']['id']=="segmentDayFour":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							dayFourList.append([childElements[0]['props']['children'][0], location])

				if child['props']['id']=="segmentDayFive":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							dayFiveList.append([childElements[0]['props']['children'][0], location])

				if child['props']['id']=="segmentDaySix":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							daySixList.append([childElements[0]['props']['children'][0], location])

				if child['props']['id']=="segmentDaySeven":
					temp = child['props']['children'][1]['props']['children']
					for adbox in temp:
						childElements = adbox['props']['children']
						if len(childElements[3]['props']['values'])==1:
							location = ast.literal_eval(childElements[2]['props']['children'][0])
							daySevenList.append([childElements[0]['props']['children'][0], location])
			except:
				print("Not found")

		response = json.loads(api_base_response)
		propertyNode = response[-1]
		print(str(propertyNode))
		masterGraph = []
		masterGraph.append(identifyNodesEdges(dayOneList,propertyNode))
		masterGraph.append(identifyNodesEdges(dayTwoList,propertyNode))
		masterGraph.append(identifyNodesEdges(dayThreeList,propertyNode))
		masterGraph.append(identifyNodesEdges(dayFourList,propertyNode))
		masterGraph.append(identifyNodesEdges(dayFiveList,propertyNode))
		masterGraph.append(identifyNodesEdges(daySixList,propertyNode))
		masterGraph.append(identifyNodesEdges(daySevenList,propertyNode))
		print("**********************MASTER GRAPH****************************")
		print(str(masterGraph))
		print("**************************************************************")

		onlyAttractionsList=[]
		onlyAttractionsList.extend(dayOneList)
		onlyAttractionsList.extend(dayTwoList)
		onlyAttractionsList.extend(dayThreeList)
		onlyAttractionsList.extend(dayFourList)
		onlyAttractionsList.extend(dayFiveList)
		onlyAttractionsList.extend(daySixList)
		onlyAttractionsList.extend(daySevenList)

		masterGraph.append(onlyAttractionsList)
		masterGraph.append(propertyNode)

		return(json.dumps(masterGraph))
	else:
		return None


@app.callback(Output('graphImage','src'), [Input('graph_api_response', 'children')])
def plotNetworkGraph(children):
	print("Calling plotNetworkGraph...")
	if children is None:
		return None
	else:
		constructGraph(children)
		time.sleep(3)
		print("Serving network image")
		image_filename = '/tmp/graphnetwork.png'
		encoded_image = base64.b64encode(open(image_filename, 'rb').read())
		return ('data:image/png;base64,{}'.format(encoded_image.decode()))


@app.callback(Output('download_excel_button', 'href'), [Input('graph_api_response', 'children')])
def generateExcel(children):
	print("Calling generateExcel...")
	if children is None:
		return None
	else:
		graph_api_response = json.loads(children)
		propertyNode = graph_api_response[-1][0]
		totalDayList=graph_api_response[:-2]

		formattedList = []
		for idx, dayList in enumerate(totalDayList, 1):
			if(len(dayList)!=0):
				firstNodeFound = 0

				while(firstNodeFound==0):
					for edge in dayList:
						if(edge[0][0]==propertyNode):
							firstNodeFound = 1
							currentNode = edge[0][1]
							formattedList.append({'Day':idx, 'Start':propertyNode, 'End':edge[0][1], 'Distance':edge[1]})
							dayList.remove(edge)
							break

				while(firstNodeFound==0):
					for edge in dayList:
						if(edge[0][1]==propertyNode):
							firstNodeFound = 1
							currentNode = edge[0][0]
							formattedList.append({'Day':idx, 'Start':propertyNode, 'End':edge[0][0], 'Distance':edge[1]})
							dayList.remove(edge)
							break

				while (len(dayList)!=0):
					currentNodeFound = 0
					for edge in dayList:
						if(edge[0][0]==currentNode):
							formattedList.append({'Day':idx, 'Start':currentNode, 'End':edge[0][1], 'Distance':edge[1]})
							currentNode = edge[0][1]
							dayList.remove(edge)
							currentNodeFound = 1
							break
					if(currentNodeFound==0):
						for edge in dayList:
							if(edge[0][1]==currentNode):
								formattedList.append({'Day':idx, 'Start':currentNode, 'End':edge[0][0], 'Distance':edge[1]})
								currentNode = edge[0][0]
								dayList.remove(edge)
								break

		excel_download_url = generate_excel_file(formattedList)
		return (excel_download_url)

# =============================
# Allocates locations to days
# =============================

@app.callback(Output('outputDayOne', 'children'), [Input('api_base_response', 'children')])
def updateOutputOne(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=1):
			limitedResponse = api_response[1][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 1))
		else:
			return None

@app.callback(Output('segmentDayOne', 'style'), [Input('api_base_response', 'children')])
def showSegmentOne(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=1):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

@app.callback(Output('outputDayTwo', 'children'), [Input('api_base_response', 'children')])
def updateOutputTwo(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=2):
			limitedResponse = api_response[2][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 2))
		else:
			return None

@app.callback(Output('segmentDayTwo', 'style'), [Input('api_base_response', 'children')])
def showSegmentTwo(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=2):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

@app.callback(Output('outputDayThree', 'children'), [Input('api_base_response', 'children')])
def updateOutputThree(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=3):
			limitedResponse = api_response[3][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 3))
		else:
			return None

@app.callback(Output('segmentDayThree', 'style'), [Input('api_base_response', 'children')])
def showSegmentThree(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=3):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

@app.callback(Output('outputDayFour', 'children'), [Input('api_base_response', 'children')])
def updateOutputFour(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=4):
			limitedResponse = api_response[4][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 4))
		else:
			return None

@app.callback(Output('segmentDayFour', 'style'), [Input('api_base_response', 'children')])
def showSegmentFour(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=4):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

@app.callback(Output('outputDayFive', 'children'), [Input('api_base_response', 'children')])
def updateOutputFive(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=5):
			limitedResponse = api_response[5][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 5))
		else:
			return None

@app.callback(Output('segmentDayFive', 'style'), [Input('api_base_response', 'children')])
def showSegmentFive(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=5):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

@app.callback(Output('outputDaySix', 'children'), [Input('api_base_response', 'children')])
def updateOutputSix(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=6):
			limitedResponse = api_response[6][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 6))
		else:
			return None

@app.callback(Output('segmentDaySix', 'style'), [Input('api_base_response', 'children')])
def showSegmentSix(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=6):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

@app.callback(Output('outputDaySeven', 'children'), [Input('api_base_response', 'children')])
def updateOutputSeven(api_response):
	if (api_response is None):
		return None
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=7):
			limitedResponse = api_response[7][:12]
			cols = ['Attraction', 'Location', 'Type']
			df = pd.DataFrame(limitedResponse, columns=cols)
			return(display_output(df, 7))
		else:
			return None

@app.callback(Output('segmentDaySeven', 'style'), [Input('api_base_response', 'children')])
def showSegmentSeven(api_response):
	if (api_response is None):
		return ({'display':'none'})
	else:
		api_response = json.loads(api_response)
		if (api_response[0]>=7):
			return({'display':'inline'})
		else:
			return ({'display':'none'})

# =============================
# Toggle colours of boxes
# =============================

@app.callback(Output('adbox1-0', 'style'), [Input('adboxCheckbox1-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-1', 'style'), [Input('adboxCheckbox1-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-2', 'style'), [Input('adboxCheckbox1-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-3', 'style'), [Input('adboxCheckbox1-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-4', 'style'), [Input('adboxCheckbox1-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-5', 'style'), [Input('adboxCheckbox1-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-6', 'style'), [Input('adboxCheckbox1-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-7', 'style'), [Input('adboxCheckbox1-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-8', 'style'), [Input('adboxCheckbox1-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox1-9', 'style'), [Input('adboxCheckbox1-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-10', 'style'), [Input('adboxCheckbox1-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox1-11', 'style'), [Input('adboxCheckbox1-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}


@app.callback(Output('adbox2-0', 'style'), [Input('adboxCheckbox2-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-1', 'style'), [Input('adboxCheckbox2-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-2', 'style'), [Input('adboxCheckbox2-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-3', 'style'), [Input('adboxCheckbox2-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-4', 'style'), [Input('adboxCheckbox2-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-5', 'style'), [Input('adboxCheckbox2-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-6', 'style'), [Input('adboxCheckbox2-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-7', 'style'), [Input('adboxCheckbox2-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-8', 'style'), [Input('adboxCheckbox2-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox2-9', 'style'), [Input('adboxCheckbox2-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-10', 'style'), [Input('adboxCheckbox2-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox2-11', 'style'), [Input('adboxCheckbox2-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-0', 'style'), [Input('adboxCheckbox3-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-1', 'style'), [Input('adboxCheckbox3-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-2', 'style'), [Input('adboxCheckbox3-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-3', 'style'), [Input('adboxCheckbox3-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-4', 'style'), [Input('adboxCheckbox3-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-5', 'style'), [Input('adboxCheckbox3-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-6', 'style'), [Input('adboxCheckbox3-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-7', 'style'), [Input('adboxCheckbox3-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-8', 'style'), [Input('adboxCheckbox3-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox3-9', 'style'), [Input('adboxCheckbox3-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-10', 'style'), [Input('adboxCheckbox3-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox3-11', 'style'), [Input('adboxCheckbox3-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
@app.callback(Output('adbox4-0', 'style'), [Input('adboxCheckbox4-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-1', 'style'), [Input('adboxCheckbox4-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-2', 'style'), [Input('adboxCheckbox4-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-3', 'style'), [Input('adboxCheckbox4-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-4', 'style'), [Input('adboxCheckbox4-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-5', 'style'), [Input('adboxCheckbox4-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-6', 'style'), [Input('adboxCheckbox4-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-7', 'style'), [Input('adboxCheckbox4-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-8', 'style'), [Input('adboxCheckbox4-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox4-9', 'style'), [Input('adboxCheckbox4-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-10', 'style'), [Input('adboxCheckbox4-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox4-11', 'style'), [Input('adboxCheckbox4-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
@app.callback(Output('adbox5-0', 'style'), [Input('adboxCheckbox5-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-1', 'style'), [Input('adboxCheckbox5-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-2', 'style'), [Input('adboxCheckbox5-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-3', 'style'), [Input('adboxCheckbox5-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-4', 'style'), [Input('adboxCheckbox5-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-5', 'style'), [Input('adboxCheckbox5-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-6', 'style'), [Input('adboxCheckbox5-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-7', 'style'), [Input('adboxCheckbox5-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-8', 'style'), [Input('adboxCheckbox5-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox5-9', 'style'), [Input('adboxCheckbox5-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-10', 'style'), [Input('adboxCheckbox5-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox5-11', 'style'), [Input('adboxCheckbox5-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
@app.callback(Output('adbox6-0', 'style'), [Input('adboxCheckbox6-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-1', 'style'), [Input('adboxCheckbox6-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-2', 'style'), [Input('adboxCheckbox6-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-3', 'style'), [Input('adboxCheckbox6-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-4', 'style'), [Input('adboxCheckbox6-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-5', 'style'), [Input('adboxCheckbox6-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-6', 'style'), [Input('adboxCheckbox6-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-7', 'style'), [Input('adboxCheckbox6-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-8', 'style'), [Input('adboxCheckbox6-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox6-9', 'style'), [Input('adboxCheckbox6-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-10', 'style'), [Input('adboxCheckbox6-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox6-11', 'style'), [Input('adboxCheckbox6-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
@app.callback(Output('adbox7-0', 'style'), [Input('adboxCheckbox7-0', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-1', 'style'), [Input('adboxCheckbox7-1', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-2', 'style'), [Input('adboxCheckbox7-2', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-3', 'style'), [Input('adboxCheckbox7-3', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-4', 'style'), [Input('adboxCheckbox7-4', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-5', 'style'), [Input('adboxCheckbox7-5', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-6', 'style'), [Input('adboxCheckbox7-6', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-7', 'style'), [Input('adboxCheckbox7-7', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-8', 'style'), [Input('adboxCheckbox7-8', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}
        
@app.callback(Output('adbox7-9', 'style'), [Input('adboxCheckbox7-9', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-10', 'style'), [Input('adboxCheckbox7-10', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}

@app.callback(Output('adbox7-11', 'style'), [Input('adboxCheckbox7-11', 'values')])
def toggleColor(values):
    if (len(values)==1):
        return {'backgroundColor':'#ebebeb'}
    else:
        return {'backgroundColor':'transparent'}


#  ==============================================================================================================================


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=5000)

# Execute the following to run server:
# gunicorn --bind unix:/var/tmp/dash.sock --log-level=debug --timeout 1200 --preload --workers 5 index:app.server