# -*- coding: utf-8 -*-
"""Untitled

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/JimKing100/SF_Real_Estate_Live/blob/master/SF_Map_Code_Final.ipynb

## The San Francisco Real Estate Project
"""

# Install fiona - need to comment out for transfer to live site.
# Turn on for running in a notebook
#%%capture
#!pip install fiona

# Install geopandas - need to comment out for tranfer to live site.
# Turn on for running in a notebook
#%%capture
#!pip install geopandas

# Import libraries
import pandas as pd
import numpy as np
import math

import geopandas
import json

from bokeh.io import output_notebook, show, output_file
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter
from bokeh.palettes import brewer

from bokeh.io.doc import curdoc
from bokeh.models import Slider, HoverTool, Select
from bokeh.layouts import widgetbox, row, column

"""### Load and Clean the Data"""

# Load SF real estate data - 10 years (2009-2018) of single family home sales in San Francisco downloaded from the SF MLS
# Longitude and latitude were added to the csv file prior to loading using geocoding.geo.census.gov 
initial_data = pd.read_csv('https://raw.githubusercontent.com/JimKing100/SF_Real_Estate_Live/master/data/SF-SFR-Sales-Final1.csv')

# Rename subdistr_desc to neighborhood
temp_data = initial_data.rename(columns={'subdist_desc': 'neighborhood'})

# Check the data
print(temp_data.shape)
temp_data.head(5)

# Fill house square foot zero values with the average house square footage by bedroom for all single family homes in SF
averagesf_data = temp_data.groupby('beds').sf.mean()

# Use average sf by bedroom for each 0 value in each bedroom group up to 9 bedrooms
for i in range(0, 9): 
  temp_data.loc[(temp_data['sf'] == 0) & (temp_data['beds'] == i), 'sf'] = averagesf_data.loc[i]

# Use 10,000sf for anything over 9 bedrooms
temp_data.loc[temp_data['sf'] == 0, 'sf'] = 10000
temp_data = temp_data.astype({'sf': int})

# Map MLS neighborhood code (e.g. 1010) to GeoDataFrame neighborhood id (e.g. '1a') to create the sf_data for all 10 years
neighborhood_dict = {1010: '1a', 1020: '1b', 1030: '1c', 1040: '1d', 1050: '1e', 1060: '1f', 1070: '1g',
                     2010: '2a', 2020: '2b', 2030: '2c', 2040: '2d', 2050: '2e', 2060: '2f', 2070: '2g',
                     3010: '3a', 3020: '3b', 3030: '3c', 3040: '3d', 3050: '3e', 3060: '3f', 3070: '3g', 3080: '3h', 3090: '3j',
                     4010: '4a', 4020: '4b', 4030: '4c', 4040: '4d', 4050: '4e', 4060: '4f', 4070: '4g', 4080: '4h', 4090: '4j', 4100: '4k', 4110: '4m', 4120: '4n', 4130: '4p', 4140: '4r', 4150: '4s', 4160: '4t',
                     5010: '5a', 5020: '5b', 5030: '5c', 5040: '5d', 5050: '5e', 5060: '5f', 5070: '5g', 5080: '5h', 5090: '5j', 5100: '5k', 5110: '5m',
                     6010: '6a', 6020: '6b', 6030: '6c', 6040: '6d', 6050: '6e', 6060: '6f',
                     7010: '7a', 7020: '7b', 7030: '7c', 7040: '7d', 
                     8010: '8a', 8020: '8b', 8030: '8c', 8040: '8d', 8050: '8e', 8060: '8f', 8070: '8g', 8080: '8h', 8090: '8j',
                     9010: '9a', 9020: '9c', 9030: '9d', 9040: '9e', 9050: '9f', 9060: '9h', 9070: '9j', 9080: '9g', 
                     10010: '10a', 10020: '10b', 10030: '10c', 10040: '10d', 10050: '10e', 10060: '10f', 10070: '10g', 10080: '10h', 10090: '10j', 10100: '10k', 10110: '10m', 10120: '10n'
                    }
sf_data = temp_data.replace({'subdist_no': neighborhood_dict})

# Create a year column based on the sale date
sf_data['year'] = '20' + sf_data['sale_date'].str[-2:]
sf_data.head(5)

# Create a price_sf column
sf_data['price_sf'] = sf_data['sale_price'] / sf_data['sf']
sf_data.head(5)

"""### Create the Summary Data by Neighborhood"""

# Function to calculate the monthly housing payment (PITI)
def minimum_income(median_price):
    int_rate = .04
    term = 30
    down_pmt = .20
    principal_pmt = median_price * (1 - down_pmt)
    
    # Calculate insurance and taxes
    tax_pmt = (median_price * .01) / 12
    insurance_pmt = (median_price * .0038) / 12
    
    # monthly rate from annual percentage rate
    interest_rate = int_rate/(100 * 12)
    
    # total number of payments
    payment_num = term * 12
    
    # calculate monthly mortgage payment
    mortgage_pmt = principal_pmt * (interest_rate * (math.pow((1 + interest_rate), (payment_num))) / 
                               (math.pow((1 + interest_rate), (payment_num)) - 1))
    payment = mortgage_pmt + tax_pmt + insurance_pmt
    min_income = (payment / .30) * 12
    
    return min_income

neighborhood_data = sf_data.groupby(
    ['year', 'subdist_no']
).agg(
    {
    'sale_price': ['count', 'mean', 'median'],
    'sf': ['mean'],
    'price_sf': ['mean']
    }
)

#Reset the index to 1 level to fill in year
neighborhood_data = neighborhood_data.set_axis(neighborhood_data.columns.map('_'.join), axis=1, inplace=False)
neighborhood_data = neighborhood_data.reset_index(level=[0,1])

# Change data types to integer for price_sf and year
neighborhood_data = neighborhood_data.astype({'sale_price_mean': 'int'})
neighborhood_data = neighborhood_data.astype({'sale_price_median': 'int'})
neighborhood_data = neighborhood_data.astype({'sf_mean': 'int'})
neighborhood_data = neighborhood_data.astype({'price_sf_mean': 'int'})
neighborhood_data = neighborhood_data.astype({'year': 'int'})

# Add the monthly income required to buy the median house in the neighborhood
neighborhood_data['min_income'] = neighborhood_data.apply(lambda x: minimum_income(x['sale_price_median']), axis=1)
neighborhood_data = neighborhood_data.astype({'min_income': 'int'})

neighborhood_data.head()

"""### Prepare the mapping data and GeoDataFrame"""

# Read the geojson map file for Realtor Neighborhoods into a GeoDataframe object
sf = geopandas.read_file('https://raw.githubusercontent.com/JimKing100/SF_Real_Estate_Live/master/data/Realtor%20Neighborhoods.geojson')

# Set the Coordinate Referance System (crs) for projections
# ESPG code 4326 is also referred to as WGS84 lat-long projection
sf.crs = {'init': 'epsg:4326'}

# Rename columns in geojson map file
sf = sf.rename(columns={'geometry': 'geometry','nbrhood':'neighborhood_name', 'nid': 'subdist_no'}).set_geometry('geometry')

# Change neighborhood id (subdist_no) for correct code for Mount Davidson Manor and for parks
sf.loc[sf['neighborhood_name'] == 'Mount Davidson Manor', 'subdist_no'] = '4n'
sf.loc[sf['neighborhood_name'] == 'Golden Gate Park', 'subdist_no'] = '12a'
sf.loc[sf['neighborhood_name'] == 'Presidio', 'subdist_no'] = '12b'
sf.loc[sf['neighborhood_name'] == 'Lincoln Park', 'subdist_no'] = '12c'

sf.sort_values(by=['subdist_no'])
sf.head()

"""### Create colorbar formatting lookup table"""

# This dictionary contains the formatting for the data in the plots
format_data = [('sale_price_count', 0, 100,'0,0', 'Number of Sales'),
               ('sale_price_mean', 500000, 4000000,'$0,0', 'Average Sales Price'),
               ('sale_price_median', 500000, 4000000, '$0,0', 'Median Sales Price'),
               ('sf_mean', 500, 5000,'0,0', 'Average Square Footage'),
               ('price_sf_mean', 0, 2000,'$0,0', 'Average Price Per Square Foot'),
               ('min_income', 50000, 600000,'$0,0', 'Minimum Income Required')
              ]
 
#Create a DataFrame object from the dictionary 
format_df = pd.DataFrame(format_data, columns = ['field' , 'min_range', 'max_range' , 'format', 'verbage'])
format_df.head(10)

"""### Create the Interactive Plot"""

# Create a function the returns json_data for the year selected by the user
def json_data(selectedYear):
    yr = selectedYear
    
    # Pull selected year from neighborhood summary data
    df_yr = neighborhood_data[neighborhood_data['year'] == yr]
    
    # Merge the GeoDataframe object (sf) with the neighborhood summary data (neighborhood)
    merged = pd.merge(sf, df_yr, on='subdist_no', how='left')
    
    # Fill the null values
    values = {'year': yr, 'sale_price_count': 0, 'sale_price_mean': 0, 'sale_price_median': 0,
              'sf_mean': 0, 'price_sf_mean': 0, 'min_income': 0}
    merged = merged.fillna(value=values)
    
    # Bokeh uses geojson formatting, representing geographical features, with json
    # Convert to json
    merged_json = json.loads(merged.to_json())
    
    # Convert to json preferred string-like object 
    json_data = json.dumps(merged_json)
    return json_data
  
# Define the callback function: update_plot
def update_plot(attr, old, new):
    # The input yr is the year selected from the slider
    yr = slider.value
    new_data = json_data(yr)
    
    # The input cr is the criteria selected from the select box
    cr = select.value
    input_field = format_df.loc[format_df['verbage'] == cr, 'field'].iloc[0]
    
    # Update the plot based on the changed inputs
    p = make_plot(input_field)
    
    # Update the layout, clear the old document and display the new document
    layout = column(p, widgetbox(select), widgetbox(slider))
    curdoc().clear()
    curdoc().add_root(layout)
    
    # Update the data
    geosource.geojson = new_data 
    
# Create a plotting function
def make_plot(field_name):    
  # Set the format of the colorbar
  min_range = format_df.loc[format_df['field'] == field_name, 'min_range'].iloc[0]
  max_range = format_df.loc[format_df['field'] == field_name, 'max_range'].iloc[0]
  field_format = format_df.loc[format_df['field'] == field_name, 'format'].iloc[0]

  # Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
  color_mapper = LinearColorMapper(palette = palette, low = min_range, high = max_range)

  # Create color bar.
  format_tick = NumeralTickFormatter(format=field_format)
  color_bar = ColorBar(color_mapper=color_mapper, label_standoff=18, formatter=format_tick,
  border_line_color=None, location = (0, 0))

  # Create figure object.
  verbage = format_df.loc[format_df['field'] == field_name, 'verbage'].iloc[0]

  p = figure(title = verbage + ' by Neighborhood for Single Family Homes in SF by Year - 2009 to 2018', 
             plot_height = 650, plot_width = 850,
             toolbar_location = None)
  p.xgrid.grid_line_color = None
  p.ygrid.grid_line_color = None
  p.axis.visible = False

  # Add patch renderer to figure. 
  p.patches('xs','ys', source = geosource, fill_color = {'field' : field_name, 'transform' : color_mapper},
          line_color = 'black', line_width = 0.25, fill_alpha = 1)
  
  # Specify color bar layout.
  p.add_layout(color_bar, 'right')

  # Add the hover tool to the graph
  p.add_tools(hover)
  return p
    
    
# Input geojson source that contains features for plotting for:
# initial year 2018 and initial criteria sale_price_median
geosource = GeoJSONDataSource(geojson = json_data(2018))
input_field = 'sale_price_median'

# Define a sequential multi-hue color palette.
palette = brewer['Blues'][8]

# Reverse color order so that dark blue is highest obesity.
palette = palette[::-1]

# Add hover tool
hover = HoverTool(tooltips = [ ('Neighborhood','@neighborhood_name'),
                               ('# Sales', '@sale_price_count'),
                               ('Average Price', '$@sale_price_mean{,}'),
                               ('Median Price', '$@sale_price_median{,}'),
                               ('Average SF', '@sf_mean{,}'),
                               ('Price/SF ', '$@price_sf_mean{,}'),
                               ('Income Needed', '$@min_income{,}')])

# Call the plotting function
p = make_plot(input_field)

# Make a slider object: slider 
slider = Slider(title = 'Year',start = 2009, end = 2018, step = 1, value = 2018)
slider.on_change('value', update_plot)

# Make a selection object: select
select = Select(title='Select Criteria:', value='Median Sales Price', options=['Median Sales Price', 'Minimum Income Required',
                                                                               'Average Sales Price', 'Average Price Per Square Foot',
                                                                               'Average Square Footage', 'Number of Sales'])
select.on_change('value', update_plot)

# Make a column layout of widgetbox(slider) and plot, and add it to the current document
# Display the current document
layout = column(p, widgetbox(select), widgetbox(slider))
curdoc().add_root(layout)

# Use the following code to test in a notebook
# Interactive features will no show in notebook
#output_notebook()
#show(p)