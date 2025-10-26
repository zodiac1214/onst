# Rainbow Trout Stocking Locations 🐟

[![Update Data](https://github.com/zodiac1214/onst/actions/workflows/static.yml/badge.svg)](https://github.com/zodiac1214/onst/actions/workflows/static.yml)

This project fetches and displays rainbow trout stocking data from Ontario's fish stocking database, providing an interactive web page to help recreational fishers find recently stocked locations.

## Features

- **Real-time Data**: Fetches the latest rainbow trout stocking data from Ontario's ArcGIS REST API
- **Advanced Filtering**: Filter locations by:
  - **Stocking Year** (2024, 2025)
  - **Development Stage** (Adult, etc.)
  - **MNRF District** (19 districts available)
  - **Text Search** by waterbody name
- **Smart Data Grouping**: Combines multiple stocking events per location and shows:
  - Latest year's stocking count prominently
  - Total fish stocked across all years
  - Year badge indicating most recent stocking
- **Historical Data Visualization**: 
  - Interactive bar charts for each location's stocking history
  - Modal popup with Chart.js graphs
  - Detailed yearly breakdown tables
- **Detailed Information**: Each location shows:
  - Number of fish stocked (latest year vs. total)
  - Stocking year
  - Development stage (Adult, etc.)
  - MNRF District
  - Waterbody ID
  - Geographic coordinates (click to copy)
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **Interactive Features**: Search, filter, and explore data with smooth animations

## Data Source

The data is sourced from Ontario's Fish Stocking Data for Recreational Purposes via their ArcGIS REST API. The query filters for:
- **Species**: Rainbow Trout only
- **Years**: 2024-2025 stocking seasons
- **Geographic Bounds**: Ontario region (Latitude: 42.31-51.63, Longitude: -94.19 to -75.11)
- **Fish Count**: 4 to 508,680 fish per stocking event

## Usage

### Automated Updates (Recommended)

The project includes GitHub Actions workflows that automatically:
- **Fetch fresh data every hour** from the Ontario ArcGIS API
- **Update the HTML page** with any new stocking information
- **Deploy the updated page** to GitHub Pages automatically
- **Commit changes** only when new data is detected

No manual intervention required! The page stays up-to-date automatically.

### Manual Updates

If you want to run the data fetcher manually:

```bash
python3 fetch_trout_data.py
```

This will:
1. Fetch the latest rainbow trout stocking data from the API
2. Process and clean the data
3. Generate a static HTML page (`index.html`)
4. Display summary statistics

### GitHub Actions Workflows

The project includes two automated workflows:

1. **Main Update Workflow** (`static.yml`):
   - Runs every hour automatically
   - Fetches latest data from Ontario's API
   - Commits changes only if new data is found
   - Deploys updated page to GitHub Pages
   - Fully automated - no intervention needed

2. **Manual Update Workflow** (`manual-update.yml`):
   - Triggered manually from GitHub Actions tab
   - Includes debug mode and force update options
   - Useful for troubleshooting or immediate updates
   - Can force updates even when no changes detected

### Monitoring

Check the "Actions" tab in your GitHub repository to monitor:
- Hourly update status
- Data fetch success/failure
- Deployment status
- Commit history for data changes

### Viewing the Results

#### Live Website
Visit your GitHub Pages site to see the always up-to-date rainbow trout stocking locations.

#### Local Development
Open the generated `index.html` file in any web browser to view the interactive rainbow trout stocking locations map.

## Requirements

- Python 3.6+
- `requests` library

Install requirements:
```bash
pip install requests
```

## Current Data Summary

As of the last update:
- **150 unique stocking locations** (grouped from 208 raw records)
- **1,215,520 rainbow trout** stocked in total across all years
- **588,200 rainbow trout** stocked in the latest year
- **19 MNRF districts** covered
- **2 years** of data available (2024-2025)

## Project Structure

```
.
├── fetch_trout_data.py    # Main data fetching and HTML generation script
├── examine_data.py        # Utility script to examine API data structure
├── index.html            # Generated static webpage (created by script)
├── README.md             # This file
└── LICENSE               # Project license
```

## API Information

**Endpoint**: `https://services1.arcgis.com/TJH5KDher0W13Kgo/arcgis/rest/services/FishStockingDataForRecreationalPurposes/FeatureServer/0/query`

**Key Parameters**:
- Format: JSON
- Species Filter: Rainbow Trout
- Year Range: 2024-2025
- Geographic bounds: Ontario region
- Output: All available fields

## Contributing

Feel free to submit issues or pull requests to improve the project. Some potential enhancements:
- Add interactive map visualization with markers
- Include more fish species (Brook Trout, Lake Trout, etc.)
- Add multi-year trend analysis
- Implement automated daily updates
- Add export functionality (CSV, PDF)
- Include weather and fishing condition data

## License

This project is open source. See the LICENSE file for details.

---

*Data provided by Ontario's Ministry of Natural Resources and Forestry (MNRF)*
