#!/usr/bin/env python3
"""
Rainbow Trout Stocking Data Fetcher
Fetches data from ArcGIS REST API and generates a static HTML page
"""

import json
import requests
from datetime import datetime
from typing import List, Dict, Any


class TroutDataFetcher:
    def __init__(self):
        self.base_url = "https://services1.arcgis.com/TJH5KDher0W13Kgo/arcgis/rest/services/FishStockingDataForRecreationalPurposes/FeatureServer/0/query"
        self.params = {
            'f': 'json',
            'where': "(Species IN ('Rainbow Trout')) AND (Stocking_Year >= 2024 AND Stocking_Year <= 2025) AND (Latitude >= 42.31 AND Latitude <= 51.63) AND (Longitude >= -94.19 AND Longitude <= -75.11) AND (Number_of_Fish_Stocked >= 4 AND Number_of_Fish_Stocked <= 508680)",
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
        Process and clean the feature data
        """
        processed_features = []
        
        for feature in data.get('features', []):
            attributes = feature.get('attributes', {})
            geometry = feature.get('geometry', {})
            
            # Extract relevant information using correct field names
            waterbody_name = (attributes.get('Official_Waterbody_Name') or 
                            attributes.get('Unoffcial_Waterbody_Name') or 
                            'Unknown Waterbody')
            
            processed_feature = {
                'location_name': waterbody_name,
                'district': attributes.get('MNRF_District', 'Unknown District'),
                'species': attributes.get('Species', 'Rainbow Trout'),
                'stocking_year': attributes.get('Stocking_Year', 'Unknown'),
                'stocking_date': f"{attributes.get('Stocking_Year', 'Unknown')}",  # Only year available
                'number_stocked': attributes.get('Number_of_Fish_Stocked', 0),
                'developmental_stage': attributes.get('Developmental_Stage', 'Unknown'),
                'latitude': attributes.get('Latitude', 0),
                'longitude': attributes.get('Longitude', 0),
                'waterbody_id': attributes.get('Waterbody_Location_Identifier', 'Unknown'),
                'geographic_township': attributes.get('Geographic_Township', 'Unknown')
            }
            
            processed_features.append(processed_feature)
        
        # Sort by district and then by waterbody name
        processed_features.sort(
            key=lambda x: (x['district'], x['location_name'])
        )
        
        return processed_features
    
    def generate_html(self, features: List[Dict[str, Any]]) -> str:
        """
        Generate HTML page with the trout stocking data
        """
        # Calculate summary statistics
        total_locations = len(features)
        total_fish = sum(f['number_stocked'] for f in features if isinstance(f['number_stocked'], (int, float)))
        districts = set(f['district'] for f in features if f['district'] and f['district'] != 'Unknown District' and f['district'].strip())
        unique_districts = len(districts)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rainbow Trout Stocking Locations 2024-2025</title>
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
            max-width: 1200px;
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
        
        .search-box {{
            margin-bottom: 2rem;
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
        
        .locations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
        }}
        
        .location-card {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .location-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        
        .card-header {{
            background: linear-gradient(135deg, #28a745 0%, #20a144 100%);
            color: white;
            padding: 1rem;
        }}
        
        .location-name {{
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.25rem;
        }}
        
        .county {{
            font-size: 0.9rem;
            opacity: 0.9;
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
        }}
        
        .last-updated {{
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-style: italic;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            h1 {{
                font-size: 2rem;
            }}
            
            .locations-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🐟 Rainbow Trout Stocking Locations</h1>
            <p class="subtitle">2024-2025 Stocking Data for Recreational Fishing</p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <span class="stat-number">{total_locations}</span>
                <div class="stat-label">Total Locations</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{total_fish:,}</span>
                <div class="stat-label">Fish Stocked</div>
            </div>
            <div class="stat-card">
                <span class="stat-number">{unique_districts}</span>
                <div class="stat-label">Districts</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" class="search-input" id="searchInput" placeholder="Search by waterbody name, district, or development stage...">
        </div>
        
        <div class="locations-grid" id="locationsGrid">
"""
        
        # Add location cards
        for feature in features:
            fish_count = feature['number_stocked']
            if isinstance(fish_count, (int, float)):
                fish_display = f"{int(fish_count):,}"
            else:
                fish_display = str(fish_count)
            
            html_content += f"""
            <div class="location-card" data-search="{feature['location_name'].lower()} {feature['district'].lower()} {feature['developmental_stage'].lower()}">
                <div class="card-header">
                    <div class="location-name">{feature['location_name']}</div>
                    <div class="county">{feature['district']}</div>
                </div>
                <div class="card-body">
                    <div class="detail-row">
                        <span class="detail-label">Fish Stocked:</span>
                        <span class="detail-value fish-count">{fish_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Stocking Year:</span>
                        <span class="detail-value">{feature['stocking_year']}</span>
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
                        <span class="detail-label">Geographic Township:</span>
                        <span class="detail-value">{feature['geographic_township']}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Coordinates:</span>
                        <span class="detail-value coordinates">{feature['latitude']:.4f}, {feature['longitude']:.4f}</span>
                    </div>
                </div>
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="last-updated">
            Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </div>
    </div>
    
    <script>
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        const locationsGrid = document.getElementById('locationsGrid');
        const locationCards = document.querySelectorAll('.location-card');
        
        searchInput.addEventListener('input', function() {{
            const searchTerm = this.value.toLowerCase();
            
            locationCards.forEach(card => {{
                const searchData = card.getAttribute('data-search');
                if (searchData.includes(searchTerm)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }});
        
        // Add click to copy coordinates
        document.querySelectorAll('.coordinates').forEach(coord => {{
            coord.style.cursor = 'pointer';
            coord.title = 'Click to copy coordinates';
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
            print("Open 'index.html' in your browser to view the results.")
            
        except Exception as e:
            print(f"Error: {e}")
            return False
        
        return True


if __name__ == "__main__":
    fetcher = TroutDataFetcher()
    fetcher.run()