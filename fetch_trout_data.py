#!/usr/bin/env python3
"""
Rainbow Trout Stocking Data Fetcher
Fetches data from ArcGIS REST API and generates a static HTML page with OpenStreetMap integration
"""

import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any


class TroutDataFetcher:
    def __init__(self):
        self.base_url = "https://services1.arcgis.com/TJH5KDher0W13Kgo/arcgis/rest/services/FishStockingDataForRecreationalPurposes/FeatureServer/0/query"
        self.params = {
            'f': 'json',
            'where': "(Species IN ('Rainbow Trout')) AND (Stocking_Year >= 2020 AND Stocking_Year <= 2025) AND (Latitude >= 42.31 AND Latitude <= 51.63) AND (Longitude >= -94.19 AND Longitude <= -75.11) AND (Number_of_Fish_Stocked >= 4 AND Number_of_Fish_Stocked <= 508680)",
            'outFields': '*'
        }
    
    def fetch_data(self) -> Dict[str, Any]:
        """
        Fetch rainbow trout stocking data from the ArcGIS API
        """
        try:
            print("Fetching rainbow trout stocking data...")
            response = requests.get(self.base_url, params=self.params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'features' not in data:
                raise ValueError("Invalid response format: missing 'features' key")
            
            print(f"Successfully fetched {len(data['features'])} records")
            return data
            
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            raise
    
    def process_features(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process and clean the feature data, grouping by location with historical data
        """
        # First, collect all raw features
        raw_features = []
        
        for feature in data.get('features', []):
            attributes = feature.get('attributes', {})
            
            # Extract relevant information using correct field names
            waterbody_name = (attributes.get('Official_Waterbody_Name') or 
                            attributes.get('Unoffcial_Waterbody_Name') or 
                            'Unknown Waterbody')
            
            raw_feature = {
                'location_name': waterbody_name,
                'district': attributes.get('MNRF_District', 'Unknown District'),
                'species': attributes.get('Species', 'Rainbow Trout'),
                'stocking_year': attributes.get('Stocking_Year', 'Unknown'),
                'number_stocked': attributes.get('Number_of_Fish_Stocked', 0),
                'developmental_stage': attributes.get('Developmental_Stage', 'Unknown'),
                'latitude': attributes.get('Latitude', 0),
                'longitude': attributes.get('Longitude', 0),
                'waterbody_id': attributes.get('Waterbody_Location_Identifier', 'Unknown'),
                'geographic_township': attributes.get('Geographic_Township', 'Unknown')
            }
            
            raw_features.append(raw_feature)
        
        # Group by unique waterbody ID (more reliable than name + district)
        location_groups = {}
        for feature in raw_features:
            # Use waterbody_id as primary key, fallback to location_name + district if ID is missing
            location_key = feature['waterbody_id'] if feature['waterbody_id'] != 'Unknown' else f"{feature['location_name']}_{feature['district']}"
            if location_key not in location_groups:
                location_groups[location_key] = []
            location_groups[location_key].append(feature)
        
        # Process each location group
        processed_features = []
        for location_key, group in location_groups.items():
            # Sort by year (most recent first)
            group.sort(key=lambda x: x['stocking_year'] if isinstance(x['stocking_year'], int) else 0, reverse=True)
            
            # Get the most recent entry as the main record
            latest = group[0]
            
            # Calculate totals
            total_all_years = sum(entry['number_stocked'] for entry in group if isinstance(entry['number_stocked'], (int, float)))
            latest_year_count = latest['number_stocked']
            
            # Get all unique development stages for this location
            dev_stages = list(set(entry['developmental_stage'] for entry in group if entry['developmental_stage'] != 'Unknown'))
            years_available = list(set(entry['stocking_year'] for entry in group if isinstance(entry['stocking_year'], int)))
            
            processed_feature = {
                'location_name': latest['location_name'],
                'district': latest['district'],
                'species': latest['species'],
                'stocking_year': latest['stocking_year'],
                'number_stocked': latest_year_count,
                'total_all_years': total_all_years,
                'developmental_stage': latest['developmental_stage'],
                'all_dev_stages': dev_stages,
                'latitude': latest['latitude'],
                'longitude': latest['longitude'],
                'waterbody_id': latest['waterbody_id'],
                'geographic_township': latest['geographic_township'],
                'years_available': years_available
            }
            
            processed_features.append(processed_feature)
        
        # Sort by latest stocking year (most recent first), then by location name
        processed_features.sort(
            key=lambda x: (x['stocking_year'] if isinstance(x['stocking_year'], int) else 0, x['location_name']),
            reverse=True
        )
        
        return processed_features
    
    def generate_html(self, features: List[Dict[str, Any]]) -> str:
        """
        Generate HTML page with the trout stocking data, multi-select filters, and OpenStreetMap
        """
        # Calculate summary statistics
        total_locations = len(features)
        total_fish_latest = sum(f['number_stocked'] for f in features if isinstance(f['number_stocked'], (int, float)))
        total_fish_all_time = sum(f['total_all_years'] for f in features if isinstance(f['total_all_years'], (int, float)))
        districts = set(f['district'] for f in features if f['district'] and f['district'] != 'Unknown District' and f['district'].strip())
        unique_districts = len(districts)
        
        # Get unique values for filters
        all_years = set()
        all_dev_stages = set()
        all_districts = set()
        
        for feature in features:
            all_years.update(feature['years_available'])
            all_dev_stages.update(feature['all_dev_stages'])
            all_districts.add(feature['district'])
        
        # Remove empty/unknown values
        all_years = sorted([y for y in all_years if isinstance(y, int)])
        all_dev_stages = sorted([s for s in all_dev_stages if s and s != 'Unknown'])
        all_districts = sorted([d for d in all_districts if d and d != 'Unknown District'])

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rainbow Trout Stocking Locations 2020-2025</title>
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, #2c5aa0 0%, #1e3d72 100%);
            color: white;
            padding: 2rem 0;
            text-align: center;
            margin-bottom: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            position: relative;
        }}
        
        .header-donation {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: #ffc107;
            color: #333;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header-donation:hover {{
            background: #e0a800;
            transform: translateY(-1px);
            box-shadow: 0 3px 6px rgba(0,0,0,0.3);
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #2c5aa0;
            display: block;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }}
        
        .stat-sublabel {{
            color: #999;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }}
        
        .filters-section {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        
        .filters-title {{
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 1rem;
            color: #2c5aa0;
        }}
        
        .filters-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        
        .filter-group {{
            display: flex;
            flex-direction: column;
        }}
        
        .filter-label {{
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #555;
        }}
        
        .multi-select {{
            position: relative;
            display: inline-block;
            width: 100%;
        }}
        
        .multi-select-display {{
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            min-height: 38px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .multi-select-display:focus {{
            border-color: #2c5aa0;
            outline: none;
        }}
        
        .multi-select-arrow {{
            transition: transform 0.2s;
        }}
        
        .multi-select-arrow.open {{
            transform: rotate(180deg);
        }}
        
        .multi-select-dropdown {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 2px solid #ddd;
            border-top: none;
            border-radius: 0 0 6px 6px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }}
        
        .multi-select-option {{
            padding: 8px 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .multi-select-option:hover {{
            background-color: #f8f9fa;
        }}
        
        .multi-select-option input[type="checkbox"] {{
            margin: 0;
        }}
        
        .search-box {{
            margin-bottom: 1rem;
            text-align: center;
        }}
        
        .search-input {{
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 25px;
            width: 100%;
            max-width: 400px;
            outline: none;
        }}
        
        .search-input:focus {{
            border-color: #2c5aa0;
        }}
        
        .clear-filters {{
            background: #dc3545;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
            width: 100%;
        }}
        
        .clear-filters:hover {{
            background: #c82333;
        }}
        
        .results-info {{
            text-align: center;
            margin-bottom: 1rem;
            color: #666;
            font-style: italic;
        }}
        
        .locations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 1.5rem;
        }}
        
        .location-card {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            position: relative;
        }}
        
        .location-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        
        .card-header {{
            background: linear-gradient(135deg, #28a745 0%, #20a144 100%);
            color: white;
            padding: 1rem;
            position: relative;
        }}
        
        /* Current year (2025) - Green */
        .location-card.current-year .card-header {{
            background: linear-gradient(135deg, #28a745 0%, #20a144 100%);
        }}
        
        /* Previous years - Yellow */
        .location-card.previous-year .card-header {{
            background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
            color: #333;
        }}
        
        .location-card.previous-year .year-badge {{
            background: rgba(255, 255, 255, 0.9);
            color: #333;
        }}
        
        .location-name {{
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.25rem;
            padding-left: 45px;
        }}
        
        .district {{
            font-size: 0.9rem;
            opacity: 0.9;
            padding-left: 45px;
        }}
        
        .year-badge {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: rgba(255,255,255,0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .card-body {{
            padding: 1rem;
        }}
        
        .detail-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            padding: 0.25rem 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .detail-row:last-child {{
            border-bottom: none;
            margin-bottom: 0;
        }}
        
        .detail-label {{
            font-weight: 600;
            color: #555;
        }}
        
        .detail-value {{
            color: #333;
        }}
        
        .fish-count {{
            background: #e3f2fd;
            color: #1565c0;
            padding: 0.25rem 0.5rem;
            border-radius: 15px;
            font-weight: bold;
        }}
        
        .coordinates {{
            font-family: monospace;
            font-size: 0.85rem;
            background: #f8f9fa;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
        }}
        
        .map-button {{
            background: #17a2b8;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 0.5rem;
            width: 100%;
            transition: background 0.2s;
        }}
        
        .map-button:hover {{
            background: #138496;
        }}
        
        /* Star/Favorite Button Styles */
        .star-button {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .star-button:hover {{
            background: rgba(255, 255, 255, 1);
            transform: scale(1.1);
        }}
        
        .star-button.starred {{
            background: #ffc107;
            color: white;
        }}
        
        .star-button.starred:hover {{
            background: #e0a800;
        }}
        
        /* Starred button on previous-year cards - use darker gold for visibility */
        .location-card.previous-year .star-button.starred {{
            background: #b8860b;
            color: white;
            border: 2px solid #8b6914;
        }}
        
        .location-card.previous-year .star-button.starred:hover {{
            background: #8b6914;
            border-color: #654321;
        }}
        
        /* Favorite Section Styles */
        .favorites-section {{
            margin-bottom: 2rem;
        }}
        
        .favorites-header {{
            background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
            color: #333;
            padding: 1rem;
            border-radius: 8px 8px 0 0;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        
        .favorites-container {{
            border: 2px solid #ffc107;
            border-radius: 0 0 8px 8px;
            padding: 1rem;
            background: #fff9e6;
        }}
        
        .no-favorites {{
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 2rem;
        }}
        
        /* Starred Section Styles */
        .starred-section {{
            margin-bottom: 2rem;
        }}
        
        .starred-header {{
            background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
            color: #333;
            padding: 1rem;
            border-radius: 8px 8px 0 0;
            font-weight: bold;
            margin-bottom: 0;
        }}
        
        .starred-header h2 {{
            margin: 0;
            font-size: 1.3rem;
        }}
        
        .starred-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1rem;
            padding: 1rem;
            background: #fff9e6;
            border: 2px solid #ffc107;
            border-top: none;
            border-radius: 0 0 8px 8px;
        }}
        
        /* Section Headers */
        .section-header {{
            background: linear-gradient(135deg, #28a745 0%, #20a144 100%);
            color: white;
            padding: 1rem;
            border-radius: 8px 8px 0 0;
            margin-bottom: 0;
            margin-top: 1rem;
        }}
        
        .section-header h2 {{
            margin: 0;
            font-size: 1.3rem;
        }}
        
        .all-locations-section .locations-grid {{
            border-top: none;
            border-radius: 0 0 8px 8px;
            border: 2px solid #28a745;
            padding: 1rem;
        }}
        
        /* Update Notification Badge */
        .update-badge {{
            position: absolute;
            top: 5px;
            left: 50px;
            background: #dc3545;
            color: white;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 10px;
            z-index: 15;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
            100% {{ opacity: 1; }}
        }}
        
        /* Modal Styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 10px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        
        .modal-title {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #2c5aa0;
        }}
        
        .close {{
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            color: #999;
        }}
        
        .close:hover {{
            color: #333;
        }}
        
        #map {{
            height: 400px;
            width: 100%;
            border-radius: 8px;
            margin: 20px 0;
        }}
        
        .location-info {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .info-label {{
            font-weight: 600;
            color: #555;
        }}
        
        .info-value {{
            color: #333;
        }}
        
        .last-updated {{
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-style: italic;
        }}
        
        .donation-section {{
            text-align: center;
            margin-top: 2rem;
            padding: 1.5rem;
            background: linear-gradient(135deg, #28a745 0%, #20a144 100%);
            border-radius: 8px;
            color: white;
        }}
        
        .donation-text {{
            margin-bottom: 1rem;
            font-size: 1rem;
        }}
        
        .donation-button {{
            background: #ffc107;
            color: #333;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 1rem;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .donation-button:hover {{
            background: #e0a800;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            h1 {{
                font-size: 2rem;
            }}
            
            .header-donation {{
                position: static;
                margin-bottom: 1rem;
                display: block;
                width: fit-content;
                margin-left: auto;
                margin-right: auto;
            }}
            
            .locations-grid {{
                grid-template-columns: 1fr;
            }}
            
            .filters-grid {{
                grid-template-columns: 1fr;
            }}
            
            .modal-content {{
                width: 95%;
                margin: 10% auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <a href="https://www.paypal.com/donate/?business=DSLQSPRCKJMAW&amount=5&no_recurring=1&currency_code=CAD" 
               target="_blank" 
               class="header-donation">
                ☕ Buy me a lure
            </a>
            <h1>🐟 Rainbow Trout Stocking Locations</h1>
            <p class="subtitle">2020-2025 Stocking Data for Recreational Fishing</p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <span class="stat-number">{total_locations}</span>
                <div class="stat-label">Total Locations</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{total_fish_latest:,}</span>
                <div class="stat-label">Fish Stocked (Latest Year)</div>
                <div class="stat-sublabel">{total_fish_all_time:,} total all years</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{unique_districts}</span>
                <div class="stat-label">Districts</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{len(all_years)}</span>
                <div class="stat-label">Years Available</div>
                <div class="stat-sublabel">{min(all_years) if all_years else 'N/A'} - {max(all_years) if all_years else 'N/A'}</div>
            </div>
        </div>
        
        <div class="filters-section">
            <div class="filters-title">🔍 Filter Locations</div>
            <div class="filters-grid">
                <div class="filter-group">
                    <label class="filter-label">Stocking Year</label>
                    <div class="multi-select" id="yearMultiSelect">
                        <div class="multi-select-display" tabindex="0">
                            <span class="selected-text">All Years</span>
                            <span class="multi-select-arrow">▼</span>
                        </div>
                        <div class="multi-select-dropdown">
                            <div class="multi-select-option">
                                <input type="checkbox" value="" id="year-all" checked>
                                <label for="year-all">All Years</label>
                            </div>"""
        
        # Add year options
        for year in sorted(all_years, reverse=True):
            html_content += f"""
                            <div class="multi-select-option">
                                <input type="checkbox" value="{year}" id="year-{year}">
                                <label for="year-{year}">{year}</label>
                            </div>"""
        
        html_content += """
                        </div>
                    </div>
                </div>
                <div class="filter-group">
                    <label class="filter-label">Development Stage</label>
                    <div class="multi-select" id="stageMultiSelect">
                        <div class="multi-select-display" tabindex="0">
                            <span class="selected-text">All Stages</span>
                            <span class="multi-select-arrow">▼</span>
                        </div>
                        <div class="multi-select-dropdown">
                            <div class="multi-select-option">
                                <input type="checkbox" value="" id="stage-all" checked>
                                <label for="stage-all">All Stages</label>
                            </div>"""
        
        # Add development stage options
        for stage in all_dev_stages:
            html_content += f"""
                            <div class="multi-select-option">
                                <input type="checkbox" value="{stage}" id="stage-{stage.replace(' ', '-').lower()}">
                                <label for="stage-{stage.replace(' ', '-').lower()}">{stage}</label>
                            </div>"""
        
        html_content += """
                        </div>
                    </div>
                </div>
                <div class="filter-group">
                    <label class="filter-label">District</label>
                    <div class="multi-select" id="districtMultiSelect">
                        <div class="multi-select-display" tabindex="0">
                            <span class="selected-text">All Districts</span>
                            <span class="multi-select-arrow">▼</span>
                        </div>
                        <div class="multi-select-dropdown">
                            <div class="multi-select-option">
                                <input type="checkbox" value="" id="district-all" checked>
                                <label for="district-all">All Districts</label>
                            </div>"""
        
        # Add district options
        for i, district in enumerate(all_districts):
            # Shorten district names for display
            display_name = district.replace(" District", "").replace("MNRF", "").strip()
            html_content += f"""
                            <div class="multi-select-option">
                                <input type="checkbox" value="{district}" id="district-{i}">
                                <label for="district-{i}">{display_name}</label>
                            </div>"""
        
        html_content += f"""
                        </div>
                    </div>
                </div>
                <div class="filter-group">
                    <label class="filter-label">&nbsp;</label>
                    <button class="clear-filters" onclick="clearAllFilters()">Clear All Filters</button>
                </div>
            </div>
            <div class="search-box">
                <input type="text" class="search-input" id="searchInput" placeholder="Search by waterbody name...">
            </div>
            <div class="results-info" id="resultsInfo">Showing all {total_locations} locations</div>
        </div>
        
        <!-- Starred Locations Section -->
        <div class="starred-section" id="starredSection" style="display: none;">
            <div class="starred-header">
                <h2>⭐ Your Starred Locations</h2>
            </div>
            <div class="starred-grid" id="starredGrid">
                <!-- Starred locations will be populated here by JavaScript -->
            </div>
        </div>
        
        <!-- All Locations Section -->
        <div class="all-locations-section">
            <div class="section-header" id="allLocationsHeader">
                <h2>🎣 All Locations</h2>
            </div>
            <div class="locations-grid" id="locationsGrid">
"""
        
        # Add location cards
        for i, feature in enumerate(features):
            fish_count = feature['number_stocked']
            if isinstance(fish_count, (int, float)):
                fish_display = f"{int(fish_count):,}"
            else:
                fish_display = str(fish_count)
            
            # Create location data JSON for JavaScript (escaped for HTML attributes)
            location_data = {
                'name': feature['location_name'],
                'district': feature['district'],
                'latitude': feature['latitude'],
                'longitude': feature['longitude'],
                'fish_count': feature['number_stocked'],
                'total_fish': feature['total_all_years'],
                'year': feature['stocking_year'],
                'stage': feature['developmental_stage'],
                'waterbody_id': feature['waterbody_id'],
                'township': feature['geographic_township']
            }
            
            # Use HTML data attributes instead of inline JSON
            location_data_attrs = []
            for key, value in location_data.items():
                attr_name = f'data-location-{key.replace("_", "-")}'
                attr_value = str(value).replace('"', '&quot;').replace("'", '&#x27;')
                location_data_attrs.append(f'{attr_name}="{attr_value}"')
            location_data_attrs_str = ' '.join(location_data_attrs)
            
            # Determine year class for styling
            current_year = 2025
            year_class = "current-year" if feature['stocking_year'] == current_year else "previous-year"
            
            html_content += f"""
            <div class="location-card {year_class}" 
                 data-search="{feature['location_name'].lower()}" 
                 data-year="{feature['stocking_year']}"
                 data-stage="{feature['developmental_stage']}"
                 data-district="{feature['district']}"
                 {location_data_attrs_str}>
                <div class="card-header">
                    <button class="star-button" onclick="toggleFavorite(this)" title="Add to favorites">
                        ⭐
                    </button>
                    <div class="location-name">{feature['location_name']}</div>
                    <div class="district">{feature['district'].replace(' District', '')}</div>
                    <div class="year-badge">{feature['stocking_year']}</div>
                </div>
                <div class="card-body">
                    <div class="detail-row">
                        <span class="detail-label">Fish Stocked ({feature['stocking_year']}):</span>
                        <span class="detail-value fish-count">{fish_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Total All Years:</span>
                        <span class="detail-value">{feature['total_all_years']:,}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Development Stage:</span>
                        <span class="detail-value">{feature['developmental_stage']}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Waterbody ID:</span>
                        <span class="detail-value">{feature['waterbody_id']}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Coordinates:</span>
                        <span class="detail-value coordinates" title="Click to copy">{feature['latitude']:.4f}, {feature['longitude']:.4f}</span>
                    </div>
                    <button class="map-button" onclick="showLocationMapFromCard(this)">
                        🗺️ View on Map
                    </button>
                </div>
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="last-updated">
            Last updated: {datetime.now(ZoneInfo('America/Toronto')).strftime('%B %d, %Y at %I:%M %p EST')}
        </div>
    </div>
    
    <!-- Modal for Location Map -->
    <div id="mapModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="modalTitle">Location Map</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div id="map"></div>
            <div class="location-info" id="locationInfo">
                <h3>Location Details</h3>
                <div class="info-grid" id="infoGrid">
                </div>
            </div>
        </div>
    </div>
    
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <script>
        let map = null;
        let currentMarker = null;
        
        // Favorites management
        function getFavorites() {{
            const favorites = localStorage.getItem('trout-favorites');
            return favorites ? JSON.parse(favorites) : [];
        }}
        
        function saveFavorites(favorites) {{
            localStorage.setItem('trout-favorites', JSON.stringify(favorites));
        }}
        
        function getLastVisit() {{
            const lastVisit = localStorage.getItem('trout-last-visit');
            return lastVisit ? new Date(lastVisit) : new Date(0);
        }}
        
        function saveLastVisit() {{
            localStorage.setItem('trout-last-visit', new Date().toISOString());
        }}
        
        function getFavoriteData() {{
            const data = localStorage.getItem('trout-favorite-data');
            return data ? JSON.parse(data) : {{}};
        }}
        
        function saveFavoriteData(data) {{
            localStorage.setItem('trout-favorite-data', JSON.stringify(data));
        }}
        
        function checkForUpdates() {{
            const favorites = getFavorites();
            const lastVisit = getLastVisit();
            const storedData = getFavoriteData();
            const currentData = {{}};
            
            let hasUpdates = false;
            
            // Collect current data for all favorite locations
            favorites.forEach(locationKey => {{
                const card = document.querySelector(`[data-location-name][data-location-district]`);
                if (card) {{
                    const cards = document.querySelectorAll('.location-card');
                    for (const c of cards) {{
                        const name = c.getAttribute('data-location-name');
                        const district = c.getAttribute('data-location-district');
                        const key = `${{name}}-${{district}}`;
                        
                        if (key === locationKey) {{
                            const fishCount = c.getAttribute('data-location-fish-count');
                            const totalFish = c.getAttribute('data-location-total-fish');
                            const year = c.getAttribute('data-location-year');
                            
                            currentData[key] = {{
                                fishCount: parseInt(fishCount),
                                totalFish: parseInt(totalFish),
                                year: parseInt(year),
                                lastUpdated: new Date().toISOString()
                            }};
                            
                            // Check if data has changed since last visit
                            const stored = storedData[key];
                            if (stored && (
                                stored.fishCount !== currentData[key].fishCount ||
                                stored.totalFish !== currentData[key].totalFish ||
                                stored.year !== currentData[key].year
                            )) {{
                                hasUpdates = true;
                                showUpdateNotification(c, name);
                            }}
                            break;
                        }}
                    }}
                }}
            }});
            
            // Save current data
            saveFavoriteData(currentData);
            
            return hasUpdates;
        }}
        
        function showUpdateNotification(card, locationName) {{
            // Add update badge to the card
            const header = card.querySelector('.card-header');
            let badge = header.querySelector('.update-badge');
            
            if (!badge) {{
                badge = document.createElement('div');
                badge.className = 'update-badge';
                badge.textContent = 'NEW';
                badge.title = 'This location has been updated since your last visit';
                header.appendChild(badge);
                
                // Show push notification if permission granted
                showPushNotification(locationName, 'Updated stocking data');
            }}
        }}
        
        function clearUpdateNotifications() {{
            document.querySelectorAll('.update-badge').forEach(badge => {{
                badge.remove();
            }});
        }}
        
        function toggleFavorite(button) {{
            const card = button.closest('.location-card');
            const locationName = card.getAttribute('data-location-name');
            const district = card.getAttribute('data-location-district');
            const locationKey = `${{locationName}}-${{district}}`;
            
            let favorites = getFavorites();
            const index = favorites.indexOf(locationKey);
            
            if (index === -1) {{
                // Add to favorites
                favorites.push(locationKey);
                button.classList.add('starred');
                button.title = 'Remove from favorites';
            }} else {{
                // Remove from favorites
                favorites.splice(index, 1);
                button.classList.remove('starred');
                button.title = 'Add to favorites';
            }}
            
            saveFavorites(favorites);
            sortLocationsByFavorites();
        }}
        
        function sortLocationsByFavorites() {{
            const container = document.querySelector('.locations-grid');
            const starredContainer = document.querySelector('.starred-grid');
            const starredSection = document.querySelector('.starred-section');
            const cards = Array.from(container.querySelectorAll('.location-card'));
            const favorites = getFavorites();
            
            // Clear starred section
            starredContainer.innerHTML = '';
            
            // Separate starred and non-starred cards
            const starredCards = [];
            const regularCards = [];
            
            cards.forEach(card => {{
                const locationName = card.getAttribute('data-location-name');
                const district = card.getAttribute('data-location-district');
                const locationKey = `${{locationName}}-${{district}}`;
                
                if (favorites.includes(locationKey)) {{
                    // Clone card for starred section
                    const clonedCard = card.cloneNode(true);
                    starredCards.push(clonedCard);
                }} else {{
                    regularCards.push(card);
                }}
            }});
            
            // Show/hide starred section based on whether there are favorites
            if (starredCards.length > 0) {{
                starredSection.style.display = 'block';
                starredCards.forEach(card => {{
                    starredContainer.appendChild(card);
                    // Reattach event listeners for cloned cards
                    const starButton = card.querySelector('.star-button');
                    const mapButton = card.querySelector('.map-button');
                    if (starButton) {{
                        starButton.onclick = function() {{ toggleFavorite(this); }};
                    }}
                    if (mapButton) {{
                        mapButton.onclick = function() {{ showLocationMapFromCard(this); }};
                    }}
                }});
            }} else {{
                starredSection.style.display = 'none';
            }}
            
            // Clear and repopulate main grid with non-starred cards
            container.innerHTML = '';
            regularCards.forEach(card => container.appendChild(card));
        }}
        
        function initializeFavorites() {{
            const favorites = getFavorites();
            const cards = document.querySelectorAll('.location-card');
            
            cards.forEach(card => {{
                const locationName = card.getAttribute('data-location-name');
                const district = card.getAttribute('data-location-district');
                const locationKey = `${{locationName}}-${{district}}`;
                const button = card.querySelector('.star-button');
                
                if (favorites.includes(locationKey)) {{
                    button.classList.add('starred');
                    button.title = 'Remove from favorites';
                }}
            }});
            
            sortLocationsByFavorites();
        }}
        
        // Multi-select functionality
        class MultiSelect {{
            constructor(element) {{
                this.element = element;
                this.display = element.querySelector('.multi-select-display');
                this.dropdown = element.querySelector('.multi-select-dropdown');
                this.arrow = element.querySelector('.multi-select-arrow');
                this.selectedText = element.querySelector('.selected-text');
                this.checkboxes = element.querySelectorAll('input[type="checkbox"]');
                this.allCheckbox = element.querySelector('input[value=""]');
                
                this.init();
            }}
            
            init() {{
                this.display.addEventListener('click', () => this.toggle());
                this.display.addEventListener('keydown', (e) => {{
                    if (e.key === 'Enter' || e.key === ' ') {{
                        e.preventDefault();
                        this.toggle();
                    }}
                }});
                
                this.checkboxes.forEach(cb => {{
                    cb.addEventListener('change', () => this.handleChange(cb));
                }});
                
                // Close dropdown when clicking outside
                document.addEventListener('click', (e) => {{
                    if (!this.element.contains(e.target)) {{
                        this.close();
                    }}
                }});
            }}
            
            toggle() {{
                const isOpen = this.dropdown.style.display === 'block';
                if (isOpen) {{
                    this.close();
                }} else {{
                    this.open();
                }}
            }}
            
            open() {{
                this.dropdown.style.display = 'block';
                this.arrow.classList.add('open');
            }}
            
            close() {{
                this.dropdown.style.display = 'none';
                this.arrow.classList.remove('open');
            }}
            
            handleChange(changedCheckbox) {{
                if (changedCheckbox === this.allCheckbox) {{
                    // If "All" is checked, uncheck others
                    if (changedCheckbox.checked) {{
                        this.checkboxes.forEach(cb => {{
                            if (cb !== this.allCheckbox) {{
                                cb.checked = false;
                            }}
                        }});
                    }}
                }} else {{
                    // If any specific option is checked, uncheck "All"
                    if (changedCheckbox.checked) {{
                        this.allCheckbox.checked = false;
                    }}
                    
                    // If no specific options are checked, check "All"
                    const specificChecked = Array.from(this.checkboxes).some(cb => 
                        cb !== this.allCheckbox && cb.checked
                    );
                    if (!specificChecked) {{
                        this.allCheckbox.checked = true;
                    }}
                }}
                
                this.updateDisplay();
                applyFilters();
            }}
            
            updateDisplay() {{
                const selected = Array.from(this.checkboxes)
                    .filter(cb => cb.checked && cb !== this.allCheckbox)
                    .map(cb => cb.nextElementSibling.textContent);
                
                if (selected.length === 0 || this.allCheckbox.checked) {{
                    this.selectedText.textContent = this.allCheckbox.nextElementSibling.textContent;
                }} else if (selected.length === 1) {{
                    this.selectedText.textContent = selected[0];
                }} else {{
                    this.selectedText.textContent = `${{selected.length}} selected`;
                }}
            }}
            
            getSelectedValues() {{
                if (this.allCheckbox.checked) {{
                    return [];
                }}
                return Array.from(this.checkboxes)
                    .filter(cb => cb.checked && cb !== this.allCheckbox)
                    .map(cb => cb.value);
            }}
        }}
        
        // Initialize multi-selects
        const yearMultiSelect = new MultiSelect(document.getElementById('yearMultiSelect'));
        const stageMultiSelect = new MultiSelect(document.getElementById('stageMultiSelect'));
        const districtMultiSelect = new MultiSelect(document.getElementById('districtMultiSelect'));
        
        // Filter functionality
        function applyFilters() {{
            const selectedYears = yearMultiSelect.getSelectedValues();
            const selectedStages = stageMultiSelect.getSelectedValues();
            const selectedDistricts = districtMultiSelect.getSelectedValues();
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            const cards = document.querySelectorAll('.location-card');
            let visibleCount = 0;
            
            cards.forEach(card => {{
                const cardYear = card.getAttribute('data-year');
                const cardStage = card.getAttribute('data-stage');
                const cardDistrict = card.getAttribute('data-district');
                const searchData = card.getAttribute('data-search');
                
                const yearMatch = selectedYears.length === 0 || selectedYears.includes(cardYear);
                const stageMatch = selectedStages.length === 0 || selectedStages.includes(cardStage);
                const districtMatch = selectedDistricts.length === 0 || selectedDistricts.includes(cardDistrict);
                const searchMatch = !searchTerm || searchData.includes(searchTerm);
                
                if (yearMatch && stageMatch && districtMatch && searchMatch) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            
            document.getElementById('resultsInfo').textContent = 
                `Showing ${{visibleCount}} of {total_locations} locations`;
        }}
        
        function clearAllFilters() {{
            // Reset all multi-selects
            [yearMultiSelect, stageMultiSelect, districtMultiSelect].forEach(ms => {{
                ms.checkboxes.forEach(cb => {{
                    if (cb.value === '') {{
                        cb.checked = true;
                    }} else {{
                        cb.checked = false;
                    }}
                }});
                ms.updateDisplay();
            }});
            
            // Clear search
            document.getElementById('searchInput').value = '';
            
            applyFilters();
        }}
        
        // Search input listener
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        
        // Map functionality
        function showLocationMapFromCard(button) {{
            // Find the parent location card
            const card = button.closest('.location-card');
            if (!card) {{
                console.error('Could not find location card');
                return;
            }}
            
            // Extract location data from data attributes
            const locationData = {{
                name: card.getAttribute('data-location-name') || 'Unknown',
                district: card.getAttribute('data-location-district') || 'Unknown',
                latitude: parseFloat(card.getAttribute('data-location-latitude')) || 0,
                longitude: parseFloat(card.getAttribute('data-location-longitude')) || 0,
                fish_count: parseInt(card.getAttribute('data-location-fish-count')) || 0,
                total_fish: parseInt(card.getAttribute('data-location-total-fish')) || 0,
                year: card.getAttribute('data-location-year') || 'Unknown',
                stage: card.getAttribute('data-location-stage') || 'Unknown',
                waterbody_id: card.getAttribute('data-location-waterbody-id') || 'Unknown',
                township: card.getAttribute('data-location-township') || 'Unknown'
            }};
            
            showLocationMap(locationData);
        }}
        
        function showLocationMap(locationData) {{
            document.getElementById('modalTitle').textContent = `Map: ${{locationData.name}}`;
            
            // Initialize map if not already done
            if (!map) {{
                map = L.map('map');
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }}).addTo(map);
            }}
            
            // Remove existing marker
            if (currentMarker) {{
                map.removeLayer(currentMarker);
            }}
            
            // Add new marker
            currentMarker = L.marker([locationData.latitude, locationData.longitude])
                .addTo(map)
                .bindPopup(`<b>${{locationData.name}}</b><br>
                           Fish Stocked (${{locationData.year}}): ${{locationData.fish_count.toLocaleString()}}<br>
                           District: ${{locationData.district}}`);
            
            // Set map view
            map.setView([locationData.latitude, locationData.longitude], 13);
            
            // Update location info
            const infoGrid = document.getElementById('infoGrid');
            infoGrid.innerHTML = `
                <div class="info-item">
                    <span class="info-label">Location:</span>
                    <span class="info-value">${{locationData.name}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">District:</span>
                    <span class="info-value">${{locationData.district}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Fish Stocked (${{locationData.year}}):</span>
                    <span class="info-value">${{locationData.fish_count.toLocaleString()}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Total All Years:</span>
                    <span class="info-value">${{locationData.total_fish.toLocaleString()}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Development Stage:</span>
                    <span class="info-value">${{locationData.stage}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Coordinates:</span>
                    <span class="info-value">${{locationData.latitude.toFixed(4)}}, ${{locationData.longitude.toFixed(4)}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Waterbody ID:</span>
                    <span class="info-value">${{locationData.waterbody_id}}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Township:</span>
                    <span class="info-value">${{locationData.township}}</span>
                </div>
            `;
            
            // Show modal
            document.getElementById('mapModal').style.display = 'block';
            
            // Invalidate size after showing modal to fix map display
            setTimeout(() => {{
                if (map) {{
                    map.invalidateSize();
                }}
            }}, 100);
        }}
        
        function closeModal() {{
            document.getElementById('mapModal').style.display = 'none';
        }}
        
        // Close modal when clicking outside
        window.onclick = function(event) {{
            const modal = document.getElementById('mapModal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
        
        // Add click to copy coordinates
        document.querySelectorAll('.coordinates').forEach(coord => {{
            coord.addEventListener('click', function() {{
                navigator.clipboard.writeText(this.textContent).then(() => {{
                    const original = this.textContent;
                    this.textContent = 'Copied!';
                    setTimeout(() => {{
                        this.textContent = original;
                    }}, 1000);
                }});
            }});
        }});
        
        // Initialize favorites when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            initializeFavorites();
            checkForUpdates();
            initializePushNotifications();
            
            // Save visit time when user leaves the page
            window.addEventListener('beforeunload', function() {{
                saveLastVisit();
                clearUpdateNotifications();
            }});
        }});
        
        // Push notification functionality
        function initializePushNotifications() {{
            // Check if browser supports notifications
            if ('Notification' in window) {{
                // Request permission for notifications
                if (Notification.permission === 'default') {{
                    const favorites = getFavorites();
                    if (favorites.length > 0) {{
                        Notification.requestPermission().then(permission => {{
                            if (permission === 'granted') {{
                                console.log('Notification permission granted');
                            }}
                        }});
                    }}
                }}
            }}
        }}
        
        function showPushNotification(locationName, updateType) {{
            if (Notification.permission === 'granted') {{
                const notification = new Notification('Trout Stocking Update', {{
                    body: `${{locationName}} has new stocking data (${{updateType}})`,
                    icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMzIiIGZpbGw9IiMyOGE3NDUiLz4KPHN2ZyB4PSIxNiIgeT0iMTYiIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+CjxwYXRoIGQ9Ik0xMiAyYzUuNTIzIDAgMTAgNC40NzcgMTAgMTBzLTQuNDc3IDEwLTEwIDEwUzIgMTcuNTIzIDIgMTJTNi40NzcgMiAxMiAyeiIvPgo8L3N2Zz4KPC9zdmc+',
                    tag: 'trout-update',
                    requireInteraction: false,
                    silent: false
                }});
                
                // Auto-close notification after 5 seconds
                setTimeout(() => {{
                    notification.close();
                }}, 5000);
                
                // Handle notification click
                notification.onclick = function() {{
                    window.focus();
                    notification.close();
                }};
            }}
        }}
    </script>
</body>
</html>"""
        
        return html_content
    
    def save_html(self, html_content: str, filename: str = 'index.html'):
        """
        Save the HTML content to a file
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML page saved as '{filename}'")
        except IOError as e:
            print(f"Error saving HTML file: {e}")
            raise
    
    def run(self):
        """
        Main execution function
        """
        try:
            # Fetch data from API
            raw_data = self.fetch_data()
            
            # Process the data
            processed_features = self.process_features(raw_data)
            
            if not processed_features:
                print("No rainbow trout stocking data found.")
                return
            
            # Generate HTML
            html_content = self.generate_html(processed_features)
            
            # Save HTML file
            self.save_html(html_content)
            
            print(f"\\nSuccess! Generated static page with {len(processed_features)} rainbow trout stocking locations.")
            print("Features added:")
            print("✅ Multi-select dropdown filters with checkboxes")
            print("✅ Fixed filter stacking issues")
            print("✅ Removed historical charts")
            print("✅ Added OpenStreetMap integration")
            print("✅ Interactive location maps with detailed popups")
            print("Open 'index.html' in your browser to view the results.")
            
        except Exception as e:
            print(f"Error: {e}")
            return False
        
        return True


if __name__ == "__main__":
    fetcher = TroutDataFetcher()
    fetcher.run()