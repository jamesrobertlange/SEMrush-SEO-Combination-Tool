import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import urlparse
import json
import io
import zipfile
import base64

# Set page config first
st.set_page_config(page_title="SEMrush SEO Combo Tool by Jimmy Lange", layout="wide")

# Updated CSS with execution button styling
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

    /* Execute Button Styling */
    .execute-button {
        margin: 2rem auto;
        text-align: center;
    }
    
    .execute-button button {
        background-color: rgb(76, 175, 80) !important;
        font-size: 1.2rem !important;
        padding: 1rem 2rem !important;
        min-width: 200px !important;
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
    column_mapping = {
        "Keyword": "keyword",
        "Position": "position",
        "Search Volume": "search_volume",
        "Keyword Intents": "keyword_intents",
        "URL": "url",
        "Traffic": "traffic",
        "Timestamp": "timestamp"
    }
    
    top_pages_sem = top_pages_sem[list(column_mapping.keys())].rename(columns=column_mapping)
    
    # Clean and process Traffic column and convert to integer
    top_pages_sem.loc[:, 'traffic'] = top_pages_sem['traffic'].replace(',', '', regex=True).astype(int)
    top_pages_sem = top_pages_sem.sort_values(by='traffic', ascending=False)
    
    # Process timestamps
    top_pages_sem['timestamp'] = pd.to_datetime(top_pages_sem['timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    top_pages_sem['month'] = pd.to_datetime(top_pages_sem['timestamp'], errors='coerce').dt.strftime('%Y-%m')
    top_pages_sem['date'] = top_pages_sem['month'].astype(str) + "-11"
    top_pages_sem = top_pages_sem.drop(['month', 'timestamp'], axis=1)

    # Process branded keywords if provided
    if branded_terms:
        def brandedKWS(series):
            pattern = '|'.join(r'\b{}\b'.format(term.strip()) for term in branded_terms)
            return series.str.lower().str.contains(pattern, na=False, regex=True)
        top_pages_sem["branded"] = brandedKWS(top_pages_sem["keyword"])

    # Create a copy for segment analysis
    analysis_df = top_pages_sem.copy()
    analysis_df['segment'] = analysis_df['url'].apply(get_segment)
    
    # Add segments to main output if requested
    if include_segments:
        top_pages_sem['segment'] = analysis_df['segment']
    
    # Calculate segment occurrences
    segment_occurrences = analysis_df['segment'].value_counts()

    # Analyze segments
    def agg_keywords_and_urls(group):
        sorted_group = group.sort_values('traffic', ascending=False)
        keywords = sorted_group['keyword'].tolist()[:3]
        urls = sorted_group['url'].tolist()[:3]
        traffic_sum = group['traffic'].sum()
        occurrences = segment_occurrences.get(group.name, 0)
        
        return pd.Series({
            'traffic': traffic_sum,
            'keyword': keywords,
            'url': urls,
            'occurrences': occurrences
        }, name=group.name)

    segment_analysis = analysis_df.groupby('segment').apply(agg_keywords_and_urls).reset_index()
    segment_analysis = segment_analysis.sort_values('traffic', ascending=False)

    # Create partial segment analysis
    partial_segment_analysis = segment_analysis[
        (segment_analysis['occurrences'] > 5) & 
        (segment_analysis['occurrences'] <= 50)
    ]

    # Format traffic values with commas
    for df in [top_pages_sem, segment_analysis, partial_segment_analysis]:
        if 'traffic' in df.columns:
            df_copy = df.copy()
            df_copy.loc[:, 'traffic'] = df_copy['traffic'].apply(lambda x: f"{x:,}" if isinstance(x, (int, float)) else x)
            df = df_copy

    return top_pages_sem, segment_analysis, partial_segment_analysis

def convert_df_to_csv(df):
    """Convert dataframe to CSV string once"""
    return df.to_csv(index=False)

def reset_app():
    # Clear all the stored data
    st.session_state.csv_strings = {
        'combined': None,
        'full_segment': None,
        'partial_segment': None
    }
    # Clear any other session state variables you might have
    if 'uploaded_files' in st.session_state:
        del st.session_state.uploaded_files

def main():
    # Initialize session states
    if 'executed' not in st.session_state:
        st.session_state.executed = False
    if 'csv_strings' not in st.session_state:
        st.session_state.csv_strings = {
            'combined': None,
            'full_segment': None,
            'partial_segment': None
        }

    # Title and subtitle
    st.markdown("# SEMrush Organic Position Combo Tool")
    st.markdown("created by [Jimmy Lange](https://jamesrobertlange.com)", unsafe_allow_html=True)
    
    # Add segment explanation
    st.markdown("""
    This tool analyzes your SEMrush Organic Overview data, removes duplicates, and groups relevant data together for SEO analysis. 
                
    This is used to get over keyword limits to get full datasets. For instance, setting filters for Page 1 (under your SEMrush limit), and then for more Pages. Those CSVs then get combined in this tool for analysis elsewhere.
    
    A segment is the last meaningful part of your URL path (e.g., for '/blog/seo-tips', the segment is 'seo-tips').
    This helps identify which sections of your site drive the most organic traffic.
    """)

    # Initialize variables
    top_pages_sem = None
    full_segment_analysis = None
    partial_segment_analysis = None
    
    # Sidebar controls
    with st.sidebar:
        st.header("Settings")
        
        # Add reset button to sidebar
        st.sidebar.markdown("### Reset Tool")
        if st.sidebar.button("🔄 Reset All", type="primary"):
            reset_app()
            st.rerun()

        # File upload with size limit warning
        st.markdown("""
            ### Upload CSV Files
            
            ⚠️ **File Size Limits**
            - Larger files may cause performance issues
        """)
        
        uploaded_files = st.file_uploader(
            "Upload SEMrush CSV files",
            type=['csv'],
            accept_multiple_files=True,
            label_visibility="hidden"
        )
        
        # Check file sizes
        files_valid = True
        if uploaded_files:
            for file in uploaded_files:
                file_size = file.size / (1024 * 1024)  # Convert to MB
                if file_size > 200:
                    st.error(f"⚠️ {file.name} is {file_size:.1f}MB. Files over 200MB may fail to process.")
                    files_valid = False
        

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

    # Execute button (only show if files are uploaded)
    if uploaded_files:
        st.markdown('<div class="execute-button">', unsafe_allow_html=True)
        execute_button = st.button("▶️ Execute Analysis", type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if execute_button and files_valid:
            st.session_state.executed = True
            
        if not files_valid:
            st.error("Please fix file size issues before executing.")
    else:
        st.info("Please upload CSV files to begin")
        st.session_state.executed = False

    # Only process if executed is True
    if st.session_state.executed and files_valid:
        with st.spinner("Processing files..."):
            try:
                # Process the files
                top_pages_sem, full_segment_analysis, partial_segment_analysis = process_csv_files(
                    uploaded_files,
                    max_position,
                    branded_terms,
                    include_segments
                )

                # Convert DataFrames to CSV strings once and store in session state
                st.session_state.csv_strings['combined'] = convert_df_to_csv(top_pages_sem)
                st.session_state.csv_strings['full_segment'] = convert_df_to_csv(full_segment_analysis)
                st.session_state.csv_strings['partial_segment'] = convert_df_to_csv(partial_segment_analysis)
                
                st.success(f"Total rows processed: {len(top_pages_sem)}")

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
                        st.info("No segments match the partial analysis criteria")
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
                st.session_state.executed = False

if __name__ == "__main__":
    main()