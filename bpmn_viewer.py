"""
Enhanced BPMN Viewer Module
Supports both embedded bpmn-js viewer and external demo.bpmn.io integration
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import urllib.parse
from typing import Tuple, Optional


class BPMNViewer:
    """
    Enhanced BPMN Viewer with dual viewing options:
    1. Embedded bpmn-js viewer (local rendering)
    2. External demo.bpmn.io viewer (full editing)
    """

    # External viewer URL
    BPMN_IO_URL = "https://demo.bpmn.io"

    @staticmethod
    def render_bpmn(bpmn_xml: str, height: int = 600) -> dict:
        """Render BPMN XML using bpmn-js viewer in Streamlit"""

        # Encode BPMN XML for safe embedding
        encoded_xml = base64.b64encode(bpmn_xml.encode('utf-8')).decode('utf-8')

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BPMN Viewer</title>
            <script src="https://unpkg.com/bpmn-js@17.0.2/dist/bpmn-viewer.development.js"></script>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }}
                #canvas {{
                    width: 100%;
                    height: {height - 60}px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background: #fafafa;
                }}
                .error {{
                    color: #d32f2f;
                    padding: 12px 16px;
                    background: #ffebee;
                    border: 1px solid #ef9a9a;
                    border-radius: 8px;
                    margin: 10px 0;
                    font-size: 14px;
                }}
                .success {{
                    color: #2e7d32;
                    padding: 12px 16px;
                    background: #e8f5e9;
                    border: 1px solid #a5d6a7;
                    border-radius: 8px;
                    margin: 10px 0;
                    font-size: 14px;
                }}
                .loading {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 14px;
                }}
                .toolbar {{
                    display: flex;
                    gap: 8px;
                    margin-bottom: 8px;
                }}
                .toolbar button {{
                    padding: 6px 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background: white;
                    cursor: pointer;
                    font-size: 12px;
                }}
                .toolbar button:hover {{
                    background: #f5f5f5;
                }}
            </style>
        </head>
        <body>
            <div id="status" class="loading">Loading BPMN viewer...</div>
            <div class="toolbar">
                <button onclick="zoomIn()">Zoom In</button>
                <button onclick="zoomOut()">Zoom Out</button>
                <button onclick="fitToView()">Fit to View</button>
                <button onclick="resetZoom()">Reset</button>
            </div>
            <div id="canvas"></div>

            <script>
                let viewer;
                let canvas;

                function zoomIn() {{
                    if (canvas) canvas.zoom(canvas.zoom() * 1.2);
                }}

                function zoomOut() {{
                    if (canvas) canvas.zoom(canvas.zoom() / 1.2);
                }}

                function fitToView() {{
                    if (canvas) canvas.zoom('fit-viewport');
                }}

                function resetZoom() {{
                    if (canvas) canvas.zoom(1);
                }}

                try {{
                    // Decode the BPMN XML
                    const bpmnXML = atob('{encoded_xml}');

                    // Create viewer instance
                    viewer = new BpmnJS({{
                        container: '#canvas'
                    }});

                    // Import the BPMN diagram
                    viewer.importXML(bpmnXML)
                        .then(() => {{
                            canvas = viewer.get('canvas');

                            // Zoom to fit the diagram
                            canvas.zoom('fit-viewport');

                            // Update status
                            document.getElementById('status').innerHTML =
                                '<div class="success">BPMN diagram loaded successfully</div>';

                            // Send success message to Streamlit
                            window.parent.postMessage({{
                                type: 'bpmn-render-result',
                                success: true,
                                message: 'BPMN diagram rendered successfully'
                            }}, '*');
                        }})
                        .catch((error) => {{
                            console.error('BPMN import failed:', error);
                            document.getElementById('status').innerHTML =
                                '<div class="error">Failed to load BPMN: ' + error.message + '</div>';

                            // Hide canvas on error
                            document.getElementById('canvas').style.display = 'none';

                            // Send error message to Streamlit
                            window.parent.postMessage({{
                                type: 'bpmn-render-result',
                                success: false,
                                message: error.message
                            }}, '*');
                        }});

                }} catch (error) {{
                    console.error('Failed to decode or initialize BPMN:', error);
                    document.getElementById('status').innerHTML =
                        '<div class="error">Failed to initialize BPMN viewer: ' + error.message + '</div>';
                    document.getElementById('canvas').style.display = 'none';

                    // Send error message to Streamlit
                    window.parent.postMessage({{
                        type: 'bpmn-render-result',
                        success: false,
                        message: error.message
                    }}, '*');
                }}
            </script>
        </body>
        </html>
        """

        # Render the HTML component
        result = components.html(html_content, height=height, scrolling=True)

        return result

    @staticmethod
    def render_external_viewer_url(bpmn_xml: str) -> str:
        """
        Generate URL to view BPMN in demo.bpmn.io

        Args:
            bpmn_xml: BPMN XML content

        Returns:
            URL string for external viewer
        """
        # Encode BPMN for URL
        encoded = base64.b64encode(bpmn_xml.encode('utf-8')).decode('utf-8')

        # demo.bpmn.io uses URL parameter for diagram
        viewer_url = f"https://demo.bpmn.io/new#source=data:application/bpmn+xml;base64,{encoded}"

        return viewer_url

    @staticmethod
    def render_external_viewer_iframe(bpmn_xml: str, height: int = 600) -> None:
        """
        Render demo.bpmn.io viewer in an iframe

        Note: This may have CORS restrictions
        """
        url = BPMNViewer.render_external_viewer_url(bpmn_xml)

        # Create iframe HTML
        iframe_html = f"""
        <iframe
            src="{url}"
            width="100%"
            height="{height}px"
            frameborder="0"
            style="border: 1px solid #ddd; border-radius: 8px;"
        ></iframe>
        """

        components.html(iframe_html, height=height + 20)

    @staticmethod
    def render_external_viewer_link(bpmn_xml: str) -> str:
        """
        Generate HTML link to open BPMN in external viewer

        Args:
            bpmn_xml: BPMN XML content

        Returns:
            HTML anchor tag string
        """
        url = BPMNViewer.render_external_viewer_url(bpmn_xml)

        link_html = f'''
        <a href="{url}" target="_blank"
           style="display: inline-flex; align-items: center; gap: 8px;
                  color: #1976d2; text-decoration: none;
                  padding: 10px 20px; border: 2px solid #1976d2;
                  border-radius: 8px; font-weight: 500;
                  transition: all 0.2s ease;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
            </svg>
            Open in BPMN.io Editor
        </a>
        '''

        return link_html

    @staticmethod
    def create_download_link(bpmn_xml: str, filename: str = "process.bpmn") -> str:
        """Create a download link for the BPMN file"""
        b64 = base64.b64encode(bpmn_xml.encode()).decode()
        href = f'''
        <a href="data:application/xml;base64,{b64}" download="{filename}"
           style="display: inline-flex; align-items: center; gap: 8px;
                  color: #388e3c; text-decoration: none;
                  padding: 10px 20px; border: 2px solid #388e3c;
                  border-radius: 8px; font-weight: 500;
                  transition: all 0.2s ease;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
            </svg>
            Download BPMN File
        </a>
        '''
        return href

    @staticmethod
    def validate_and_display_error(bpmn_xml: str) -> Tuple[bool, str]:
        """Validate BPMN XML and return validation result"""
        try:
            import xml.etree.ElementTree as ET

            # Parse XML
            root = ET.fromstring(bpmn_xml)

            # Check for BPMN namespace
            bpmn_ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
            if bpmn_ns not in bpmn_xml:
                return False, "Missing BPMN 2.0 namespace declaration"

            # Check for process element
            process_elements = root.findall(".//{%s}process" % bpmn_ns)
            if not process_elements:
                return False, "No process element found"

            # Check process has ID
            process = process_elements[0]
            if not process.get('id'):
                return False, "Process element missing 'id' attribute"

            # Check for executable flag (warning only)
            if process.get('isExecutable') != 'true':
                # This is a warning, not an error - still valid for viewing
                pass

            return True, "BPMN XML is valid"

        except ET.ParseError as e:
            return False, f"XML parsing error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def render_viewer_selector(bpmn_xml: str, default_mode: str = "embedded") -> None:
        """
        Render viewer mode selector in Streamlit

        Args:
            bpmn_xml: BPMN XML content
            default_mode: "embedded" or "external"
        """
        col1, col2 = st.columns([2, 1])

        with col1:
            viewer_mode = st.radio(
                "Viewer Mode",
                ["Embedded (bpmn-js)", "External (demo.bpmn.io)"],
                horizontal=True,
                index=0 if default_mode == "embedded" else 1
            )

        with col2:
            # Always show external link
            st.markdown(
                BPMNViewer.render_external_viewer_link(bpmn_xml),
                unsafe_allow_html=True
            )

        st.markdown("---")

        if viewer_mode == "Embedded (bpmn-js)":
            BPMNViewer.render_bpmn(bpmn_xml, height=600)
        else:
            st.info("Click the link above to open in BPMN.io Editor")
            # Try iframe (may have CORS issues)
            try:
                BPMNViewer.render_external_viewer_iframe(bpmn_xml, height=600)
            except Exception:
                st.warning("External viewer iframe not available. Please use the link above.")


class BPMNMinimap:
    """
    Minimap overlay for large BPMN diagrams
    """

    @staticmethod
    def render_with_minimap(bpmn_xml: str, height: int = 700) -> None:
        """
        Render BPMN with minimap overlay

        Args:
            bpmn_xml: BPMN XML content
            height: Total height including minimap
        """
        encoded_xml = base64.b64encode(bpmn_xml.encode('utf-8')).decode('utf-8')

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BPMN Viewer with Minimap</title>
            <script src="https://unpkg.com/bpmn-js@17.0.2/dist/bpmn-navigated-viewer.development.js"></script>
            <script src="https://unpkg.com/diagram-js-minimap@4.0.0/dist/diagram-js-minimap.umd.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/diagram-js-minimap@4.0.0/assets/diagram-js-minimap.css">
            <style>
                body {{ margin: 0; padding: 0; }}
                #canvas {{
                    width: 100%;
                    height: {height - 50}px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background: white;
                }}
                .djs-minimap {{
                    position: absolute;
                    right: 20px;
                    top: 20px;
                    border: 2px solid #ccc;
                    border-radius: 4px;
                    background: white;
                }}
                .status {{
                    padding: 8px 16px;
                    font-family: sans-serif;
                    font-size: 14px;
                }}
                .success {{ color: #2e7d32; background: #e8f5e9; }}
                .error {{ color: #d32f2f; background: #ffebee; }}
            </style>
        </head>
        <body>
            <div id="status" class="status">Loading...</div>
            <div id="canvas"></div>

            <script>
                try {{
                    const bpmnXML = atob('{encoded_xml}');

                    const viewer = new BpmnJS({{
                        container: '#canvas',
                        additionalModules: [
                            window.DiagramJSMinimap
                        ],
                        minimap: {{
                            open: true
                        }}
                    }});

                    viewer.importXML(bpmnXML)
                        .then(() => {{
                            const canvas = viewer.get('canvas');
                            canvas.zoom('fit-viewport');
                            document.getElementById('status').className = 'status success';
                            document.getElementById('status').textContent = 'Diagram loaded';
                        }})
                        .catch((error) => {{
                            document.getElementById('status').className = 'status error';
                            document.getElementById('status').textContent = 'Error: ' + error.message;
                        }});
                }} catch (error) {{
                    document.getElementById('status').className = 'status error';
                    document.getElementById('status').textContent = 'Error: ' + error.message;
                }}
            </script>
        </body>
        </html>
        """

        components.html(html_content, height=height, scrolling=True)


def render_dual_viewer(bpmn_xml: str) -> None:
    """
    Convenience function to render BPMN with all viewer options

    Args:
        bpmn_xml: BPMN XML content
    """
    st.subheader("BPMN Visualization")

    # Validation
    is_valid, error_msg = BPMNViewer.validate_and_display_error(bpmn_xml)

    if is_valid:
        st.success("Valid BPMN 2.0 XML")

        # Export options
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                BPMNViewer.create_download_link(bpmn_xml, "process.bpmn"),
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                BPMNViewer.render_external_viewer_link(bpmn_xml),
                unsafe_allow_html=True
            )

        with col3:
            if st.button("Copy XML to Clipboard"):
                st.code(bpmn_xml[:500] + "..." if len(bpmn_xml) > 500 else bpmn_xml)

        st.markdown("---")

        # Viewer
        BPMNViewer.render_bpmn(bpmn_xml, height=600)

    else:
        st.error(f"BPMN Validation Error: {error_msg}")

        # Still show XML for debugging
        with st.expander("View Raw BPMN XML", expanded=False):
            st.code(bpmn_xml, language="xml")
