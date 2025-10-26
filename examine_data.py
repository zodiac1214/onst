#!/usr/bin/env python3
"""
Quick script to examine the structure of the rainbow trout data
"""

import json
import requests

def examine_data():
    url = "https://services1.arcgis.com/TJH5KDher0W13Kgo/arcgis/rest/services/FishStockingDataForRecreationalPurposes/FeatureServer/0/query"
    params = {
        'f': 'json',
        'where': "(Species IN ('Rainbow Trout')) AND (Stocking_Year >= 2024 AND Stocking_Year <= 2025) AND (Latitude >= 42.31 AND Latitude <= 51.63) AND (Longitude >= -94.19 AND Longitude <= -75.11) AND (Number_of_Fish_Stocked >= 4 AND Number_of_Fish_Stocked <= 508680)",
        'outFields': '*',
        'resultRecordCount': 5  # Just get first 5 records to examine
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if 'features' in data and data['features']:
        print("Sample feature structure:")
        print(json.dumps(data['features'][0], indent=2))
        
        print("\n\nAll available fields in attributes:")
        for key in data['features'][0]['attributes'].keys():
            print(f"- {key}")
    
    if 'fields' in data:
        print("\n\nField definitions:")
        for field in data['fields']:
            print(f"- {field['name']}: {field.get('type', 'unknown')} - {field.get('alias', 'no alias')}")

if __name__ == "__main__":
    examine_data()