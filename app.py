import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import urlparse
import json
import io
import zipfile
import base64
import re  # Add re import for regex operations

# Set page config first
st.set_page_config(page_title="SEMrush SEO Combo Tool by Jimmy Lange", layout="wide")

# Updated CSS with more specific selectors
st.markdown("""
<style>
    /* Style upload text like Settings */
    [data-testid="stFileUploadDropzone"] label {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: rgb(250, 250, 250) !important;
    }
    
    /* Button Base Styles - More specific targeting */
    .stDownloadButton button, 
    .stButton button {
        background-color: rgb(38, 39, 48) !important;
        border: 1px solid rgb(70, 72, 82) !important;
        border-radius: 4px !important;
        padding: 0.75rem 1rem !important;
        width: 100% !important;
        color: rgb(250, 250, 250) !important;
    }
    
    /* Main Download Button */
    [data-testid="stDownloadButton"]:first-of-type button {
        min-height: 100px !important;
        font-size: 1.2rem !important;
        max-width: 800px !important;
        margin: 2rem auto !important;
        display: block !important;
    }
    
    /* Secondary Download Buttons */
    div.row-widget.stHorizontal [data-testid="stDownloadButton"] button {
        min-height: 75px !important;
        font-size: 1.1rem !important;
        width: 100% !important;
    }
    
    /* Fix button container widths */
    div.row-widget.stHorizontal > div {
        flex: 1;
    }
    
    /* Center containers */
    div.block-container {
        padding-top: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Download All Results ZIP styling */
    div.zip-container {
        background-color: rgb(38, 39, 48);
        border: 1px solid rgb(70, 72, 82);
        padding: 1.5rem;
        border-radius: 4px;
        text-align: center;
        max-width: 800px;
        margin: 2rem auto;
    }
    
    .zip-container a {
        color: rgb(76, 175, 80) !important;
        text-decoration: none;
        font-weight: 500;
        font-size: 1.2rem;
        display: block;
    }
    
    /* Additional Downloads text */
    .divider {
        text-align: center;
        color: rgba(250, 250, 250, 0.6);
        margin: 2rem 0;
    }
    
    /* Validation error styling */
    .validation-warning {
        background-color: #FF9800;
        color: white;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    /* Process button styling */
    .process-button {
        background-color: #4CAF50 !important;
        color: white !important;
        font-weight: bold !important;
        padding: 1rem !important;
        margin-top: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

def get_segment(url):
    parsed_url = urlparse(str(url))
    path = parsed_url.path.strip('/')
    segments = path.split('/')
    
    if not segments or (len(segments) == 1 and not segments[0]):
        return 'home'
    elif '.' in segments[-1]:
        return segments[-1].split('.')[0]
    else:
        return segments[-1]

@st.cache_data
def process_csv_files(uploaded_files, max_position, branded_terms, include_segments=False):
    # Read and combine CSV files
    dfs = [pd.read_csv(file) for file in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df.drop_duplicates(inplace=True)
    combined_df.reset_index(drop=True, inplace=True)

    # Filter by position
    top_pages_sem = combined_df[combined_df["Position"] <= max_position]
    
    # Select and rename columns to lowercase with underscores
    # Updated to include Trends and CPC
    column_mapping = {
        "Keyword": "keyword",
        "Position": "position",
        "Search Volume": "search_volume",
        "Keyword Intents": "keyword_intents",
        "URL": "url",
        "Traffic": "traffic",
        "Timestamp": "timestamp",
        "CPC": "cpc",             # Added CPC
        "Trends": "trends"        # Added Trends
    }
    
    # Check if the required columns exist in the DataFrame
    available_columns = [col for col in column_mapping.keys() if col in top_pages_sem.columns]
    
    # Only use columns that actually exist in the data
    top_pages_sem = top_pages_sem[available_columns].rename(columns={col: column_mapping[col] for col in available_columns})
    
    # Clean and process Traffic column and convert to integer
    if 'traffic' in top_pages_sem.columns:
        # Handle string values with commas and convert to numeric safely
        top_pages_sem.loc[:, 'traffic'] = pd.to_numeric(
            top_pages_sem['traffic'].astype(str).str.replace(',', '', regex=True),
            errors='coerce'
        ).fillna(0).astype('int64')
        
        # Sort by traffic
        top_pages_sem = top_pages_sem.sort_values(by='traffic', ascending=False)
    
    # Process CPC - handle missing or different formats
    if 'cpc' in top_pages_sem.columns:
        # Replace empty strings with NaN and convert to float
        top_pages_sem['cpc'] = pd.to_numeric(top_pages_sem['cpc'], errors='coerce')
        # Fill NaN with 0
        top_pages_sem['cpc'] = top_pages_sem['cpc'].fillna(0)
    
    # Process Trends - convert string representation of list to actual list if needed
    if 'trends' in top_pages_sem.columns:
        # Check if trends are in list format as string and convert to actual list
        if top_pages_sem['trends'].dtype == 'object':
            try:
                # Try to convert string representation of list to actual list
                top_pages_sem['trends'] = top_pages_sem['trends'].apply(
                    lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') and x.endswith(']') else x
                )
            except:
                # If conversion fails, keep as is
                pass
    
    # Process timestamps
    if 'timestamp' in top_pages_sem.columns:
        top_pages_sem['timestamp'] = pd.to_datetime(top_pages_sem['timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
        top_pages_sem['month'] = pd.to_datetime(top_pages_sem['timestamp'], errors='coerce').dt.strftime('%Y-%m')
        top_pages_sem['date'] = top_pages_sem['month'].astype(str) + "-11"
        top_pages_sem = top_pages_sem.drop(['month', 'timestamp'], axis=1)

    # Process branded keywords if provided
    if branded_terms and 'keyword' in top_pages_sem.columns:
        def brandedKWS(series):
            # Create a pattern that doesn't use match groups to avoid the warning
            # Use word boundaries for more accurate matching
            pattern = '|'.join(r'\b' + re.escape(term.strip()) + r'\b' for term in branded_terms)
            return series.str.lower().str.contains(pattern, na=False, regex=True)
        
        # Make sure we import re at the top of the file
        top_pages_sem["branded"] = brandedKWS(top_pages_sem["keyword"])
        
        # Log the number of branded keywords found
        branded_count = top_pages_sem["branded"].sum()
        st.session_state['branded_count'] = int(branded_count)
        st.session_state['branded_terms_used'] = branded_terms

    # Create a copy for segment analysis
    analysis_df = top_pages_sem.copy()
    analysis_df['segment'] = analysis_df['url'].apply(get_segment)
    
    # Add segments to main output if requested
    if include_segments:
        top_pages_sem['segment'] = analysis_df['segment']
    
    # Calculate segment occurrences - this is where the problem is
    # Instead of just counting, we need to count unique URLs per segment
    segment_occurrences = analysis_df.groupby('segment')['url'].nunique()

    # Analyze segments
    def agg_keywords_and_urls(group):
        # Get the segment name from the first row to avoid operating on grouping columns
        segment_name = group['segment'].iloc[0] if 'segment' in group.columns else None
        
        sorted_group = group.sort_values('traffic', ascending=False) if 'traffic' in group.columns else group
        
        # Basic aggregation
        result = {
            'occurrences': segment_occurrences.get(segment_name, 0)
        }
        
        # Add traffic if it exists
        if 'traffic' in group.columns:
            result['traffic'] = group['traffic'].sum()
        
        # Add keywords if they exist
        if 'keyword' in group.columns:
            result['keyword'] = sorted_group['keyword'].tolist()[:3]
        
        # Add URLs if they exist
        if 'url' in group.columns:
            result['url'] = sorted_group['url'].tolist()[:3]
        
        # Add CPC if it exists
        if 'cpc' in group.columns:
            result['cpc'] = group['cpc'].mean()
        
        # Add trends data aggregation if it exists
        if 'trends' in group.columns:
            # Try to aggregate trends data, handling possible string representations
            try:
                # Extract valid trend lists and calculate average for each position
                valid_trends = []
                for trend in group['trends']:
                    if isinstance(trend, list) and all(isinstance(x, (int, float)) for x in trend):
                        valid_trends.append(trend)
                
                if valid_trends:
                    # Calculate average trend for each position
                    avg_trends = []
                    for i in range(min(len(t) for t in valid_trends)):
                        avg_trends.append(sum(t[i] for t in valid_trends if i < len(t)) / len(valid_trends))
                    result['avg_trends'] = avg_trends
            except:
                # If aggregation fails, skip trends
                pass
        
        return pd.Series(result)

    # Use include_groups=False to avoid the deprecation warning
    segment_analysis = analysis_df.groupby('segment', as_index=False).apply(
        agg_keywords_and_urls, include_groups=False
    )
    
    # Sort by traffic if it exists, otherwise by occurrences
    if 'traffic' in segment_analysis.columns:
        segment_analysis = segment_analysis.sort_values('traffic', ascending=False)
    else:
        segment_analysis = segment_analysis.sort_values('occurrences', ascending=False)

    # Create partial segment analysis using the corrected occurrences values
    partial_segment_analysis = segment_analysis[
        (segment_analysis['occurrences'] > 5) & 
        (segment_analysis['occurrences'] <= 50)
    ]

    # Format traffic values with commas - avoiding the FutureWarning
    for i, df in enumerate([top_pages_sem, segment_analysis, partial_segment_analysis]):
        if 'traffic' in df.columns:
            # Create a string representation of traffic in a new column to avoid type issues
            df = df.copy()  # Create a copy to avoid SettingWithCopyWarning
            # Convert to string first to handle any non-numeric values safely
            df['traffic_formatted'] = df['traffic'].astype(str)
            # Only format values that are numeric
            numeric_mask = df['traffic'].apply(lambda x: pd.to_numeric(x, errors='coerce')).notna()
            df.loc[numeric_mask, 'traffic_formatted'] = df.loc[numeric_mask, 'traffic'].apply(
                lambda x: f"{int(float(x)):,}" if pd.notna(x) else "0"
            )
            # Store both columns - the original numeric for calculations and the formatted for display
            df['traffic_original'] = df['traffic']
            df['traffic'] = df['traffic_formatted']
            df = df.drop('traffic_formatted', axis=1)
            
            # Reassign to the original variables
            if i == 0:
                top_pages_sem = df
            elif i == 1:
                segment_analysis = df
            else:
                partial_segment_analysis = df

    return top_pages_sem, segment_analysis, partial_segment_analysis

def convert_df_to_csv(df):
    """Convert dataframe to CSV string once"""
    return df.to_csv(index=False)

def main():
    # Initialize session state for storing CSV strings and processing state
    if 'csv_strings' not in st.session_state:
        st.session_state.csv_strings = {
            'combined': None,
            'full_segment': None,
            'partial_segment': None
        }
    
    if 'branded_count' not in st.session_state:
        st.session_state.branded_count = 0
        
    if 'branded_terms_used' not in st.session_state:
        st.session_state.branded_terms_used = []
        
    if 'has_processed' not in st.session_state:
        st.session_state.has_processed = False

    # Title and subtitle
    st.markdown("# SEMrush Organic Position Combo Tool")
    st.markdown("created by [Jimmy Lange](https://jamesrobertlange.com)", unsafe_allow_html=True)
    
    # Initialize these variables to None at the start
    top_pages_sem = None
    full_segment_analysis = None
    partial_segment_analysis = None
    
    # Sidebar controls
    with st.sidebar:
        st.header("Settings")
        
        # File upload with size limit warning
        st.markdown("""
            ### Upload CSV Files
            
            ⚠️ **File Size Limits**
            - Maximum file size: 200MB per file
            - Larger files may cause performance issues
        """)
        
        uploaded_files = st.file_uploader(
            "Upload SEMrush CSV files",
            type=['csv'],
            accept_multiple_files=True,
            label_visibility="hidden"
        )
        
        # Check file sizes
        if uploaded_files:
            for file in uploaded_files:
                file_size = file.size / (1024 * 1024)  # Convert to MB
                if file_size > 200:
                    st.error(f"⚠️ {file.name} is {file_size:.1f}MB. Files over 200MB may fail to process on Streamlit Community Cloud.")
        
        # Add segment toggle in sidebar
        st.sidebar.markdown("### Output Options")
        include_segments = st.sidebar.checkbox(
            "Include Segments in Combined Output",
            value=False
        )
        
        max_position = st.number_input(
            "Maximum Position (1-100)",
            min_value=1,
            max_value=100,
            value=11
        )
        
        branded_input = st.text_input(
            "Branded Terms",
            placeholder="e.g., client name, client, client"
        ).strip()
        branded_terms = branded_input.lower().split(',') if branded_input else []
        
        # Process button instead of automatic processing
        process_button = st.button(
            "Process Files", 
            type="primary",
            help="Click to process files with current settings",
            key="process_button"
        )
        
        # Display current configuration
        st.sidebar.markdown("### Current Configuration")
        st.sidebar.write(f"Max Position: {max_position}")
        if branded_terms:
            st.sidebar.write(f"Branded Terms: {', '.join(branded_terms)}")
            if st.session_state.has_processed:
                st.sidebar.write(f"Branded Keywords Found: {st.session_state.branded_count}")
        
        # Reset button
        if st.sidebar.button("Reset All"):
            st.session_state.clear()
            st.experimental_rerun()

    # Only process files if the process button is clicked
    if uploaded_files and process_button:
        with st.spinner("Processing files..."):
            try:
                # Set processing flag
                st.session_state.has_processed = True
                
                # Process the files
                top_pages_sem, full_segment_analysis, partial_segment_analysis = process_csv_files(
                    uploaded_files,
                    max_position,
                    branded_terms,
                    include_segments
                )

                # Debug info - print counts
                st.success(f"Total rows processed: {len(top_pages_sem)}")
                
                # Add debug text for segment counts
                with st.expander("Debug Info (click to expand)"):
                    if 'occurrences' in full_segment_analysis.columns:
                        st.text(f"Segments with >5 occurrences: {len(full_segment_analysis[full_segment_analysis['occurrences'] > 5])}")
                        st.text(f"Segments with 5-50 occurrences: {len(full_segment_analysis[(full_segment_analysis['occurrences'] > 5) & (full_segment_analysis['occurrences'] <= 50)])}")
                        st.text(f"Segments total: {len(full_segment_analysis)}")
                    else:
                        st.text("No occurrences column found in segment analysis")
                        
                    if branded_terms:
                        st.text(f"Branded keywords used in processing: {', '.join(st.session_state.branded_terms_used)}")
                        st.text(f"Branded keywords found: {st.session_state.branded_count}")

                # Convert DataFrames to CSV strings once and store in session state
                st.session_state.csv_strings['combined'] = convert_df_to_csv(top_pages_sem)
                st.session_state.csv_strings['full_segment'] = convert_df_to_csv(full_segment_analysis)
                st.session_state.csv_strings['partial_segment'] = convert_df_to_csv(partial_segment_analysis)

                # Display results in tabs
                tab1, tab2, tab3 = st.tabs([
                    "Combined CSV SEMrush Output",
                    "Full Segment Analysis",
                    "Partial Segment Analysis"
                ])

                with tab1:
                    st.header("Combined CSV SEMrush Output Sample Data")
                    st.dataframe(top_pages_sem.head())

                with tab2:
                    st.header("Full Segment Analysis Sample Data")
                    st.markdown("""
                    This analysis includes ALL segments (URL paths) and their metrics, showing:
                    - Total traffic for each segment
                    - Number of times the segment appears
                    - Top 3 keywords and URLs for each segment
                    - Average CPC for each segment
                    - Aggregated trend data (when available)
                    Sorted by total traffic.
                    """)
                    st.dataframe(full_segment_analysis.head())

                with tab3:
                    st.header("Partial Segment Analysis Sample Data")
                    st.markdown("""
                    This analysis includes only segments that appear 5-50 times in the data. This helps identify:
                    - Mid-volume content areas
                    - Sections that aren't main landing pages but still drive traffic
                    - Potential optimization opportunities
                    Excludes very high-volume (>50 occurrences) and very low-volume (<5 occurrences) segments.
                    """)
                    if partial_segment_analysis.empty:
                        st.info("No segments match the partial analysis criteria (5-50 occurrences)")
                    else:
                        st.dataframe(partial_segment_analysis.head())

                # Download section
                st.markdown("## Download Results")

                # Main download button using stored CSV string
                col_main = st.container()
                with col_main:
                    st.markdown('<div class="main-download-button">', unsafe_allow_html=True)
                    st.download_button(
                        label="📥 Download Combined SEMrush CSV",
                        data=st.session_state.csv_strings['combined'],
                        file_name="combined_semrush_output.csv",
                        mime="text/csv",
                        key="main_download"
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Divider with consistent styling
                st.markdown('<div class="divider">Additional Downloads</div>', unsafe_allow_html=True)

                # Secondary downloads using stored CSV strings
                st.markdown('<div class="secondary-downloads">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📊 Full Segment Analysis",
                        data=st.session_state.csv_strings['full_segment'],
                        file_name="full_segment_analysis.csv",
                        mime="text/csv",
                        key="full_segment_download"
                    )
                
                with col2:
                    st.download_button(
                        label="📈 Partial Segment Analysis",
                        data=st.session_state.csv_strings['partial_segment'],
                        file_name="partial_segment_analysis.csv",
                        mime="text/csv",
                        key="partial_segment_download"
                    )
                st.markdown('</div>', unsafe_allow_html=True)

                # ZIP download using stored CSV strings
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("combined_semrush_output.csv", st.session_state.csv_strings['combined'])
                    zf.writestr("full_segment_analysis.csv", st.session_state.csv_strings['full_segment'])
                    zf.writestr("partial_segment_analysis.csv", st.session_state.csv_strings['partial_segment'])
                
                zip_buffer.seek(0)
                st.markdown(
                    f"""
                    <div class='zip-container'>
                        <a href="data:application/zip;base64,{base64.b64encode(zip_buffer.getvalue()).decode()}"
                           download="analysis_results.zip">
                            📦 Download All Results (ZIP)
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                # Add more detailed error information
                st.exception(e)
    elif uploaded_files:
        # Show instructions when files are uploaded but not processed
        st.info("Files uploaded. Click 'Process Files' in the sidebar when you're ready to analyze the data.")
    else:
        st.info("Please upload CSV files to begin processing")
        
    # Show configuration reminders if files are uploaded but not processed
    if uploaded_files and not process_button and not st.session_state.has_processed:
        st.warning("⚠️ Remember to set your maximum position and branded terms before processing")

if __name__ == "__main__":
    main()