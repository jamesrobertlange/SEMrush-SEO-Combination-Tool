# SEMrush CSV Combiner and Processor - Streamlit App

A Streamlit web application for processing and analyzing SEO data from multiple SEMrush CSV exports. This app combines data sources, performs segment analysis, and provides downloadable reports.

## Features

- Upload and process multiple SEMrush CSV files simultaneously
- Configurable maximum position filter (1-100)
- Custom branded terms filtering
- Optional segment inclusion in main output
- Three types of analysis outputs:
  - Combined SEMrush Output (main dataset)
  - Full Segment Analysis
  - Partial Segment Analysis

## Outputs Explained

### 1. Combined SEMrush Output
- Primary output combining all input CSV files
- Includes basic SEMrush data: keyword, position, search volume, etc.
- Optional segment column (can be toggled in sidebar)
- Branded term identification (if terms provided)
- Cleaned and standardized column names

### 2. Full Segment Analysis
- Analyzes ALL URL segments (paths) in your data
- Shows total traffic per segment
- Counts segment occurrences
- Lists top 3 keywords and URLs per segment
- Useful for understanding overall site structure performance

### 3. Partial Segment Analysis
- Focuses on "mid-volume" segments (5-50 occurrences)
- Excludes very high-volume segments (>50 occurrences)
- Excludes low-volume segments (<5 occurrences)
- Helps identify optimization opportunities in moderately-used sections
- Perfect for finding "hidden gem" content areas

## File Requirements

Input CSV files should include these columns:
- Keyword
- Position
- Search Volume
- Keyword Intents
- URL
- Traffic
- Timestamp

## Installation and Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/semrush-processor-streamlit
cd semrush-processor-streamlit
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
streamlit run app.py
```

## Usage Instructions

1. **Upload Files**
   - Use the sidebar file uploader to select one or more SEMrush CSV exports
   - Files must be under 200MB each for Streamlit Cloud deployment

2. **Configure Settings** (in sidebar)
   - Set maximum position filter (1-100)
   - Enter branded terms if needed (comma-separated)
   - Toggle segment inclusion in main output
   - Watch for file size warnings

3. **View Results**
   - Combined SEMrush Output: Main combined dataset
   - Full Segment Analysis: Complete URL path analysis
   - Partial Segment Analysis: Mid-volume segment opportunities

4. **Download Options**
   - Large centered button for main Combined SEMrush CSV
   - Secondary buttons for segment analyses
   - All-in-one ZIP download with all reports

## Size Limits

- Streamlit Community Cloud: 200MB per file
- Local deployment: Limited only by system memory
- For larger files:
  - Split files before uploading
  - Run locally
  - Use Streamlit Enterprise (if available)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.