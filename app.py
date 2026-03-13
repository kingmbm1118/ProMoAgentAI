"""
ProMoAgentAI - Enhanced Streamlit Application
Multi-agent BPMN generation with 13 specialized agents
"""

import streamlit as st
from orchestrator import BPMNOrchestrator
from bpmn_viewer import BPMNViewer, render_dual_viewer
from bpmn_uploader import BPMNUploader, create_upload_summary
from batch_processor import BatchProcessor, BatchResults
from validation import validate_bpmn_comprehensive, detect_language, get_validation_summary
from config import Config
import os
import base64

# Page configuration
st.set_page_config(
    page_title="ProMoAgentAI",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for RTL support and styling
st.markdown("""
<style>
    /* RTL support for Arabic text */
    .arabic-text {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
    }

    /* General styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
    }

    .stButton>button[data-testid="baseButton-primary"] {
        background-color: #1976d2;
    }

    /* Log entry styling */
    .log-success {
        color: #2e7d32;
        background-color: #e8f5e9;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 4px 0;
    }

    .log-error {
        color: #c62828;
        background-color: #ffebee;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 4px 0;
    }

    .log-info {
        color: #1565c0;
        background-color: #e3f2fd;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 4px 0;
    }

    /* Stats cards */
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
    }

    .stats-number {
        font-size: 2.5em;
        font-weight: bold;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = BPMNOrchestrator()
if 'workflow_result' not in st.session_state:
    st.session_state.workflow_result = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'upload_result' not in st.session_state:
    st.session_state.upload_result = None
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = None


def render_sidebar():
    """Render the sidebar with configuration and status"""
    with st.sidebar:
        st.header("Configuration")

        # Model selection display
        st.subheader("LLM Model")
        try:
            model_config = Config.get_current_model_config()
            st.info(f"**Selected:** {model_config['display_name']}")
            st.caption(f"Model ID: {model_config['model_id']}")
            st.caption(f"Provider: {model_config['provider'].upper()}")

            # Show model quality from paper
            quality_scores = {
                "sonnet-4.5": "0.95 (100% valid, 1.8 iter)",
                "gpt-5.2": "0.94 (100% valid, 1.9 iter)",
                "gemini-3": "0.97 (100% valid, 1.7 iter)"
            }
            st.caption(f"Paper results: {quality_scores.get(Config.MODEL_NAME, 'N/A')}")
        except Exception as e:
            st.error(f"Configuration error: {str(e)}")
            return False

        st.markdown("---")

        # API Key validation
        try:
            Config.validate()
            st.success(f"{model_config['provider'].upper()} API key configured")
        except ValueError as e:
            st.error(f"{str(e)}")
            st.code(f"{model_config['api_key_env']}=your_actual_key_here")
            return False

        # Camunda connection status
        st.subheader("Camunda Settings")
        st.text(f"URL: {Config.CAMUNDA_URL}")
        st.text(f"User: {Config.CAMUNDA_USERNAME}")

        st.markdown("---")

        # Session controls
        if st.button("Reset Session", type="secondary", use_container_width=True):
            st.session_state.orchestrator.reset_session()
            st.session_state.workflow_result = None
            st.session_state.upload_result = None
            st.session_state.batch_results = None
            st.session_state.processing = False
            st.rerun()

        # Session memory status
        if st.session_state.orchestrator.session_memory.original_description:
            st.subheader("Session Status")
            memory = st.session_state.orchestrator.session_memory
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Fix Attempts", len(memory.fix_attempts))
                st.metric("Valid BPMN", "" if memory.is_valid_bpmn else "")
            with col2:
                st.metric("Deploy Attempts", len(memory.camunda_deployment_attempts))
                st.metric("Deployed", "" if memory.is_deployed_to_camunda else "")

        st.markdown("---")
        st.caption("To change model, edit MODEL_NAME in .env file")
        st.caption("Options: sonnet-4.5, gpt-5.2, gemini-3")

    return True


def render_log_entries(log_entries, title="Log"):
    """Render log entries with appropriate styling"""
    if not log_entries:
        return

    with st.expander(f"{title} ({len(log_entries)} entries)", expanded=False):
        for entry in log_entries:
            if "" in entry or "Phase" in entry and ":" in entry:
                st.success(entry)
            elif "" in entry or "failed" in entry.lower() or "error" in entry.lower():
                st.error(entry)
            elif "" in entry or "Fix" in entry:
                st.info(entry)
            else:
                st.text(entry)


def render_generate_tab():
    """Render the Generate BPMN tab"""
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("Process Description")

        # Language detection indicator
        process_description = st.text_area(
            "Describe your business process in natural language:",
            height=200,
            placeholder="Example: A customer support ticket process where tickets are created, triaged by priority, assigned to agents, resolved, and then closed with customer feedback.\n\nYou can also enter descriptions in Arabic.",
            help="Describe the steps, decision points, and flow of your business process. Arabic is supported."
        )

        # Show language detection
        if process_description:
            lang = detect_language(process_description)
            if lang == 'ar':
                st.info(" Arabic text detected - BPMN will use Arabic labels")

        # Generate button
        generate_button = st.button(
            "Generate BPMN Process",
            type="primary",
            disabled=st.session_state.processing or not process_description.strip(),
            use_container_width=True
        )

        # Process the workflow
        if generate_button and process_description.strip():
            st.session_state.processing = True

            with st.spinner("Generating and validating BPMN process..."):
                try:
                    result = st.session_state.orchestrator.execute_full_workflow(process_description)
                    st.session_state.workflow_result = result
                    st.session_state.processing = False
                    st.rerun()

                except Exception as e:
                    st.error(f"Workflow execution failed: {str(e)}")
                    st.session_state.processing = False

        # Display logs and status
        if st.session_state.workflow_result:
            result = st.session_state.workflow_result

            st.subheader("Workflow Status")
            if result["success"]:
                st.success(f"{result['final_status']}")
            else:
                st.error(f"{result['final_status']}")

            # Logs
            render_log_entries(result.get("orchestration_log", []), "Orchestration Log")
            render_log_entries(result.get("review_log", []), "Review Log")
            render_log_entries(result.get("fix_log", []), "Validation & Fix Log")
            render_log_entries(result.get("deployment_log", []), "Deployment Log")

            # Download options
            if result["bpmn_xml"]:
                st.subheader("Export")
                col_dl1, col_dl2 = st.columns(2)

                with col_dl1:
                    st.markdown(
                        BPMNViewer.create_download_link(result["bpmn_xml"], "my-process.bpmn"),
                        unsafe_allow_html=True
                    )

                with col_dl2:
                    st.markdown(
                        BPMNViewer.render_external_viewer_link(result["bpmn_xml"]),
                        unsafe_allow_html=True
                    )

    with col2:
        st.header("BPMN Visualization")

        if st.session_state.processing:
            st.info("Processing your request...")

        elif st.session_state.workflow_result and st.session_state.workflow_result["bpmn_xml"]:
            result = st.session_state.workflow_result
            bpmn_xml = result["bpmn_xml"]

            # Validation status
            is_valid, error_msg = BPMNViewer.validate_and_display_error(bpmn_xml)

            if is_valid:
                st.success("Valid BPMN 2.0 XML")

                # Render viewer
                BPMNViewer.render_bpmn(bpmn_xml, height=650)

                # Show validation stats
                val_result = result.get("validation_result", {})
                if val_result:
                    stats = val_result.get("stats", {})
                    if stats:
                        st.markdown("---")
                        st.subheader("Model Statistics")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Tasks", stats.get("total_tasks", 0))
                        with col2:
                            st.metric("Gateways", stats.get("total_gateways", 0))
                        with col3:
                            st.metric("Flows", stats.get("sequence_flows", 0))
                        with col4:
                            st.metric("Lanes", stats.get("lanes", 0))

            else:
                st.error(f"BPMN Validation Error: {error_msg}")
                with st.expander("View Raw BPMN XML", expanded=False):
                    st.code(bpmn_xml, language="xml")

        else:
            st.info("Enter a process description and click 'Generate BPMN Process' to see the visualization")

            # Example descriptions
            with st.expander("Example Process Descriptions", expanded=False):
                st.markdown("""
                **Customer Support Ticket Process:**
                A customer submits a support ticket through our portal. The ticket is automatically triaged based on priority (high, medium, low). High priority tickets go directly to senior agents, while medium and low priority tickets are assigned to available agents. Agents work on the ticket and either resolve it directly or escalate to a supervisor. Once resolved, the customer is notified and asked for feedback. The ticket is then closed.

                **Purchase Order Approval:**
                An employee submits a purchase order request. If the amount is under $1000, it's automatically approved. If between $1000-5000, it requires manager approval. Above $5000 requires both manager and finance approval. Once approved, the order is sent to procurement for processing. If rejected at any stage, it's sent back to the employee with comments.

                **Employee Onboarding:**
                A new employee is hired and their information is entered into the system. HR creates an onboarding checklist including IT setup, badge creation, and training assignments. IT provisions accounts and equipment, security creates access badges, and training schedules orientation sessions. All tasks must be completed before the employee's start date.

                **Arabic Example ():**

                """)


def render_upload_tab():
    """Render the Upload & Validate tab"""
    st.header("Upload & Validate BPMN")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Upload BPMN File")

        uploaded_file = st.file_uploader(
            "Choose a BPMN or XML file",
            type=['bpmn', 'xml'],
            help="Upload an existing BPMN 2.0 file to validate and view"
        )

        if uploaded_file:
            uploader = BPMNUploader()
            result = uploader.process_upload(uploaded_file, uploaded_file.name)
            st.session_state.upload_result = result

            # Display upload result
            st.markdown("---")
            st.subheader("Upload Result")

            if result.validation.get('valid'):
                st.success("Valid BPMN 2.0 file")
            else:
                st.error("Validation failed")

            # File info
            st.markdown(f"**Filename:** {result.filename}")
            st.markdown(f"**Size:** {result.file_size / 1024:.2f} KB")

            if result.process_id:
                st.markdown(f"**Process ID:** {result.process_id}")
                st.markdown(f"**Process Name:** {result.process_name or 'N/A'}")

            # Validation details
            with st.expander("Validation Details", expanded=True):
                errors = result.validation.get('errors', [])
                warnings = result.validation.get('warnings', [])

                if errors:
                    st.markdown("**Errors:**")
                    for error in errors:
                        st.error(error)

                if warnings:
                    st.markdown("**Warnings:**")
                    for warning in warnings:
                        st.warning(warning)

                if not errors and not warnings:
                    st.success("No issues found!")

            # Stats
            stats = result.validation.get('stats', {})
            if stats:
                st.markdown("---")
                st.subheader("Model Statistics")

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.metric("Start Events", stats.get("start_events", 0))
                    st.metric("End Events", stats.get("end_events", 0))
                    st.metric("User Tasks", stats.get("user_tasks", 0))
                    st.metric("Service Tasks", stats.get("service_tasks", 0))
                with col_s2:
                    st.metric("Exclusive Gateways", stats.get("exclusive_gateways", 0))
                    st.metric("Parallel Gateways", stats.get("parallel_gateways", 0))
                    st.metric("Sequence Flows", stats.get("sequence_flows", 0))
                    st.metric("Swim Lanes", stats.get("lanes", 0))

            # Export options
            if result.can_view:
                st.markdown("---")
                st.subheader("Actions")

                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.markdown(
                        BPMNViewer.render_external_viewer_link(result.content),
                        unsafe_allow_html=True
                    )

    with col2:
        st.subheader("BPMN Visualization")

        if st.session_state.upload_result:
            result = st.session_state.upload_result

            if result.can_view and result.content:
                BPMNViewer.render_bpmn(result.content, height=650)

                with st.expander("View Raw XML", expanded=False):
                    st.code(result.content, language="xml")
            else:
                st.warning("Cannot render visualization due to validation errors")
                if result.content:
                    with st.expander("View Raw XML", expanded=True):
                        st.code(result.content, language="xml")
        else:
            st.info("Upload a BPMN file to view it here")


def render_batch_tab():
    """Render the Batch Processing tab"""
    st.header("Batch Processing")

    st.markdown("""
    Process multiple BPMN descriptions at once. Upload a text file with one process description per line,
    or separate descriptions with blank lines.
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Input")

        # File upload
        uploaded_file = st.file_uploader(
            "Upload text file with descriptions",
            type=['txt'],
            help="One description per line, or separate with blank lines"
        )

        # Or manual entry
        st.markdown("**Or enter descriptions manually:**")
        manual_input = st.text_area(
            "Enter descriptions (one per line or separated by blank lines):",
            height=200,
            placeholder="Description 1\n\nDescription 2\n\nDescription 3"
        )

        # Parse descriptions
        descriptions = []
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            processor = BatchProcessor(st.session_state.orchestrator)
            descriptions = processor.parse_descriptions(content)
            st.info(f"Found {len(descriptions)} process descriptions in file")
        elif manual_input.strip():
            processor = BatchProcessor(st.session_state.orchestrator)
            descriptions = processor.parse_descriptions(manual_input)
            st.info(f"Found {len(descriptions)} process descriptions")

        # Show preview
        if descriptions:
            with st.expander("Preview Descriptions", expanded=False):
                for i, desc in enumerate(descriptions, 1):
                    st.markdown(f"**{i}.** {desc[:100]}...")

        # Process button
        if st.button(
            "Generate All BPMN Files",
            type="primary",
            disabled=not descriptions,
            use_container_width=True
        ):
            processor = BatchProcessor(st.session_state.orchestrator)
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(current, total, status):
                progress_bar.progress(current / total)
                status_text.text(f"[{current}/{total}] {status}")

            with st.spinner("Processing batch..."):
                results = processor.process_batch(descriptions, update_progress)
                st.session_state.batch_results = results

            progress_bar.progress(1.0)
            status_text.text("Batch processing complete!")
            st.rerun()

    with col2:
        st.subheader("Results")

        if st.session_state.batch_results:
            results = st.session_state.batch_results

            # Summary stats
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Total", results.total)
            with col_r2:
                st.metric("Successful", results.successful)
            with col_r3:
                st.metric("Failed", results.failed)

            st.markdown(f"**Success Rate:** {results.success_rate:.1f}%")

            # Download options
            st.markdown("---")
            st.subheader("Download")

            # Create ZIP
            processor = BatchProcessor(st.session_state.orchestrator)
            zip_data = processor.create_zip(results)
            b64_zip = base64.b64encode(zip_data).decode()

            st.markdown(
                f'''<a href="data:application/zip;base64,{b64_zip}" download="bpmn_batch.zip"
                   style="display: inline-flex; align-items: center; gap: 8px;
                          color: white; background-color: #1976d2;
                          text-decoration: none; padding: 12px 24px;
                          border-radius: 8px; font-weight: 500;">
                    Download All as ZIP
                </a>''',
                unsafe_allow_html=True
            )

            # Individual results
            st.markdown("---")
            st.subheader("Individual Results")

            for result in results.results:
                with st.expander(
                    f"{'[SUCCESS]' if result.success else '[FAILED]'} Process {result.index}: {result.description[:50]}...",
                    expanded=False
                ):
                    if result.success:
                        st.success("Generation successful")
                        st.markdown(f"**Filename:** {result.filename}")
                        st.markdown(f"**Processing Time:** {result.processing_time:.2f}s")

                        # View button
                        if result.bpmn_xml:
                            with st.expander("View BPMN", expanded=False):
                                BPMNViewer.render_bpmn(result.bpmn_xml, height=400)

                            # Download link
                            st.markdown(
                                BPMNViewer.create_download_link(result.bpmn_xml, result.filename),
                                unsafe_allow_html=True
                            )
                    else:
                        st.error(f"Error: {result.error}")
                        st.markdown(f"**Processing Time:** {result.processing_time:.2f}s")

        else:
            st.info("No batch results yet. Upload a file or enter descriptions to process.")


def main():
    """Main application entry point"""
    st.title("ProMoAgentAI")
    st.markdown("Transform natural language business processes into validated BPMN 2.0 models using 13 specialized AI agents")

    # Render sidebar and check config
    if not render_sidebar():
        st.error("Please configure your API keys in the .env file")
        return

    # Main tabs
    tab1, tab2, tab3 = st.tabs([
        "Generate BPMN",
        "Upload & Validate",
        "Batch Processing"
    ])

    with tab1:
        render_generate_tab()

    with tab2:
        render_upload_tab()

    with tab3:
        render_batch_tab()


if __name__ == "__main__":
    main()
