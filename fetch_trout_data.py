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
        
        # Group by unique location (waterbody_name + district)
        location_groups = {}
        for feature in raw_features:
            location_key = f"{feature['location_name']}_{feature['district']}"
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
            
            # Calculate historical data
            historical_data = []
            total_all_years = 0
            years_data = {}
            
            for entry in group:
                year = entry['stocking_year']
                if year != 'Unknown' and isinstance(year, int):
                    if year not in years_data:
                        years_data[year] = 0
                    years_data[year] += entry['number_stocked']
                    total_all_years += entry['number_stocked']
            
            # Create historical data array
            for year in sorted(years_data.keys()):
                historical_data.append({
                    'year': year,
                    'fish_count': years_data[year]
                })
            
            # Get latest year's count only
            latest_year_count = years_data.get(latest['stocking_year'], latest['number_stocked'])
            
            # Get all unique development stages for this location
            dev_stages = list(set(entry['developmental_stage'] for entry in group if entry['developmental_stage'] != 'Unknown'))
            
            processed_feature = {
                'location_name': latest['location_name'],
                'district': latest['district'],
                'species': latest['species'],
                'stocking_year': latest['stocking_year'],
                'number_stocked': latest_year_count,  # Latest year only
                'total_all_years': total_all_years,   # Total across all years
                'developmental_stage': latest['developmental_stage'],
                'all_dev_stages': dev_stages,
                'latitude': latest['latitude'],
                'longitude': latest['longitude'],
                'waterbody_id': latest['waterbody_id'],
                'geographic_township': latest['geographic_township'],
                'historical_data': historical_data,
                'years_available': list(years_data.keys())
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
        Generate HTML page with the trout stocking data, filters, and historical charts
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
    <title>Rainbow Trout Stocking Locations 2024-2025</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        
        .filter-select {{
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            background: white;
            outline: none;
        }}
        
        .filter-select:focus {{
            border-color: #2c5aa0;
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
        
        .location-name {{
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.25rem;
        }}
        
        .district {{
            font-size: 0.9rem;
            opacity: 0.9;
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
        }}
        
        .history-button {{
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
        
        .history-button:hover {{
            background: #138496;
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
            max-width: 600px;
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
        
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .history-table th,
        .history-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        .history-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
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
            <h1>🐟 Rainbow Trout Stocking Locations</h1>
            <p class="subtitle">2024-2025 Stocking Data for Recreational Fishing</p>
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
                    <select class="filter-select" id="yearFilter">
                        <option value="">All Years</option>"""
        
        # Add year options
        for year in sorted(all_years, reverse=True):
            html_content += f'<option value="{year}">{year}</option>'
        
        html_content += """
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">Development Stage</label>
                    <select class="filter-select" id="stageFilter">
                        <option value="">All Stages</option>"""
        
        # Add development stage options
        for stage in all_dev_stages:
            html_content += f'<option value="{stage}">{stage}</option>'
        
        html_content += """
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">District</label>
                    <select class="filter-select" id="districtFilter">
                        <option value="">All Districts</option>"""
        
        # Add district options
        for district in all_districts:
            # Shorten district names for display
            display_name = district.replace(" District", "").replace("MNRF", "").strip()
            html_content += f'<option value="{district}">{display_name}</option>'
        
        html_content += f"""
                    </select>
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
        
        <div class="locations-grid" id="locationsGrid">
"""
        
        # Add location cards
        for i, feature in enumerate(features):
            fish_count = feature['number_stocked']
            if isinstance(fish_count, (int, float)):
                fish_display = f"{int(fish_count):,}"
            else:
                fish_display = str(fish_count)
            
            # Create historical data JSON for JavaScript
            historical_json = json.dumps(feature['historical_data'])
            
            html_content += f"""
            <div class="location-card" 
                 data-search="{feature['location_name'].lower()}" 
                 data-year="{feature['stocking_year']}"
                 data-stage="{feature['developmental_stage']}"
                 data-district="{feature['district']}">
                <div class="card-header">
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
                        <span class="detail-value coordinates">{feature['latitude']:.4f}, {feature['longitude']:.4f}</span>
                    </div>
                    <button class="history-button" onclick="showHistory('{feature['location_name']}', {historical_json})">
                        📊 View Stocking History ({len(feature['historical_data'])} years)
                    </button>
                </div>
            </div>
"""
        
        html_content += f"""
        </div>
        
        <div class="last-updated">
            Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </div>
    </div>
    
    <!-- Modal for Historical Data -->
    <div id="historyModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="modalTitle">Stocking History</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="chart-container">
                <canvas id="historyChart"></canvas>
            </div>
            <table class="history-table" id="historyTable">
                <thead>
                    <tr>
                        <th>Year</th>
                        <th>Fish Stocked</th>
                    </tr>
                </thead>
                <tbody id="historyTableBody">
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        let currentChart = null;
        
        // Filter functionality
        function applyFilters() {{
            const yearFilter = document.getElementById('yearFilter').value;
            const stageFilter = document.getElementById('stageFilter').value;
            const districtFilter = document.getElementById('districtFilter').value;
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            
            const cards = document.querySelectorAll('.location-card');
            let visibleCount = 0;
            
            cards.forEach(card => {{
                const cardYear = card.getAttribute('data-year');
                const cardStage = card.getAttribute('data-stage');
                const cardDistrict = card.getAttribute('data-district');
                const searchData = card.getAttribute('data-search');
                
                const yearMatch = !yearFilter || cardYear === yearFilter;
                const stageMatch = !stageFilter || cardStage === stageFilter;
                const districtMatch = !districtFilter || cardDistrict === districtFilter;
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
            document.getElementById('yearFilter').value = '';
            document.getElementById('stageFilter').value = '';
            document.getElementById('districtFilter').value = '';
            document.getElementById('searchInput').value = '';
            applyFilters();
        }}
        
        // Event listeners for filters
        document.getElementById('yearFilter').addEventListener('change', applyFilters);
        document.getElementById('stageFilter').addEventListener('change', applyFilters);
        document.getElementById('districtFilter').addEventListener('change', applyFilters);
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        
        // Modal functionality
        function showHistory(locationName, historicalData) {{
            document.getElementById('modalTitle').textContent = `Stocking History: ${{locationName}}`;
            
            // Clear previous chart
            if (currentChart) {{
                currentChart.destroy();
            }}
            
            // Prepare data for chart
            const years = historicalData.map(d => d.year);
            const fishCounts = historicalData.map(d => d.fish_count);
            
            // Create chart
            const ctx = document.getElementById('historyChart').getContext('2d');
            currentChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: years,
                    datasets: [{{
                        label: 'Fish Stocked',
                        data: fishCounts,
                        backgroundColor: '#28a745',
                        borderColor: '#20a144',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Number of Fish'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Year'
                            }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        title: {{
                            display: true,
                            text: 'Annual Stocking Data'
                        }}
                    }}
                }}
            }});
            
            // Populate table
            const tableBody = document.getElementById('historyTableBody');
            tableBody.innerHTML = '';
            
            historicalData.forEach(entry => {{
                const row = tableBody.insertRow();
                row.insertCell(0).textContent = entry.year;
                row.insertCell(1).textContent = entry.fish_count.toLocaleString();
            }});
            
            // Show modal
            document.getElementById('historyModal').style.display = 'block';
        }}
        
        function closeModal() {{
            document.getElementById('historyModal').style.display = 'none';
            if (currentChart) {{
                currentChart.destroy();
                currentChart = null;
            }}
        }}
        
        // Close modal when clicking outside
        window.onclick = function(event) {{
            const modal = document.getElementById('historyModal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
        
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