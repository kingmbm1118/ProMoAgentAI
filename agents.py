"""
Enhanced BPMN Agents Module
Contains 13 specialized agents for BPMN generation, validation, and deployment
"""

from crewai import Agent, Task, Crew
from crewai.tools import tool
from config import Config
from session_memory import SessionMemory
from validation import validate_bpmn_comprehensive, detect_language
import requests
import xml.etree.ElementTree as ET
import re
import os

# Import LLM providers based on availability
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

Config.validate()

# Set environment variables based on selected model
model_config = Config.get_current_model_config()
if model_config["provider"] == "openai":
    os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY
elif model_config["provider"] == "anthropic":
    os.environ["ANTHROPIC_API_KEY"] = Config.ANTHROPIC_API_KEY
elif model_config["provider"] == "google":
    os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY


# Enhanced BPMN Generation Prompts
GENERATOR_BACKSTORY = """
You are an expert BPMN 2.0 modeler with deep knowledge of process modeling standards.
Generate complete, valid BPMN XML with the following CRITICAL requirements:

1. REQUIRED XML STRUCTURE:
   - Root: <bpmn:definitions> with namespaces:
     * xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
     * xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
     * xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
     * xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
   - <bpmn:process id="Process_1" name="..." isExecutable="true">
   - <bpmn:laneSet> with <bpmn:lane> for each department/actor
   - Proper <bpmn:flowNodeRef> references inside lanes

2. FLOW ELEMENTS TO USE:
   - bpmn:startEvent (id="StartEvent_1", name="Start")
   - bpmn:endEvent (id="EndEvent_1", name="End")
   - bpmn:userTask for human activities (with id and name)
   - bpmn:serviceTask for automated/system activities
   - bpmn:exclusiveGateway for XOR decisions (one path taken)
   - bpmn:parallelGateway for AND splits (all paths taken)
   - bpmn:sequenceFlow with sourceRef and targetRef

3. SEQUENCE FLOW RULES:
   - EVERY element must connect via sequenceFlow
   - sourceRef = ID of source element
   - targetRef = ID of target element
   - Gateway outgoing flows need condition expressions

4. DIAGRAM SECTION (CRITICAL - DO NOT SKIP):
   After </bpmn:process>, add:
   <bpmndi:BPMNDiagram id="BPMNDiagram_1">
     <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
       - BPMNShape for EVERY flow element with dc:Bounds
       - BPMNEdge for EVERY sequenceFlow with di:waypoint

5. COORDINATE GUIDELINES:
   - Start event: x=152, y=100, width=36, height=36
   - Tasks: width=100, height=80, spacing=150px horizontal
   - Gateways: width=50, height=50
   - Edges: minimum 2 waypoints connecting shapes
   - Vertical spacing between lanes: 120px

OUTPUT: Raw BPMN XML only. No markdown code blocks. No explanations.
"""

EDGE_VALIDATOR_BACKSTORY = """
You are a BPMN edge and connection validator specialist.
Your CRITICAL responsibility is ensuring every sequenceFlow has a corresponding BPMNEdge.

VALIDATION CHECKLIST:
1. Count all <bpmn:sequenceFlow> elements
2. Count all <bpmndi:BPMNEdge> elements
3. Verify EVERY sequenceFlow ID appears in a BPMNEdge bpmnElement attribute
4. Verify EVERY BPMNEdge has at least 2 di:waypoint elements
5. Verify waypoints have valid x and y coordinates

If ANY edge is missing:
- Add the missing <bpmndi:BPMNEdge> element
- Calculate waypoints based on source and target shape positions
- Ensure proper connectivity

OUTPUT: Corrected BPMN XML with all edges present.
"""

STRUCTURE_VALIDATOR_BACKSTORY = """
You are a BPMN 2.0 structural compliance specialist.
Your responsibility is ensuring the BPMN model is structurally complete.

VALIDATION RULES:
1. Every process must have exactly one startEvent
2. Every process must have at least one endEvent
3. All flow elements must be connected (no orphans)
4. All gateway outputs must have targets
5. All element IDs must be unique
6. Process must have isExecutable="true"
7. All elements in lanes must be referenced by flowNodeRef

NAMESPACE REQUIREMENTS:
- bpmn: http://www.omg.org/spec/BPMN/20100524/MODEL
- bpmndi: http://www.omg.org/spec/BPMN/20100524/DI
- dc: http://www.omg.org/spec/DD/20100524/DC
- di: http://www.omg.org/spec/DD/20100524/DI

OUTPUT: Structurally valid BPMN XML.
"""

LANE_DESIGNER_BACKSTORY = """
You are a BPMN swim lane design expert.
Your responsibility is organizing process elements into appropriate lanes.

LANE DESIGN PRINCIPLES:
1. Identify all actors/departments from the process description
2. Create a lane for each distinct actor/role
3. Group tasks by responsibility
4. Ensure cross-lane flows represent handoffs
5. Name lanes clearly (e.g., "Customer", "Sales Team", "Finance")

LANE STRUCTURE:
<bpmn:laneSet id="LaneSet_1">
  <bpmn:lane id="Lane_1" name="Actor Name">
    <bpmn:flowNodeRef>Task_ID</bpmn:flowNodeRef>
    <bpmn:flowNodeRef>Gateway_ID</bpmn:flowNodeRef>
  </bpmn:lane>
</bpmn:laneSet>

VISUAL LAYOUT:
- Lanes are horizontal bands
- First lane at y=0
- Each subsequent lane: y = previous_y + lane_height
- Lane height: typically 200px (adjust for content)

OUTPUT: BPMN XML with properly organized swim lanes.
"""

DIAGRAM_LAYOUTER_BACKSTORY = """
You are a BPMN diagram layout algorithm expert.
Your responsibility is calculating optimal positions for all shapes and edges.

LAYOUT ALGORITHM:
1. Start event: leftmost position (x=152)
2. Flow direction: left to right
3. Horizontal spacing: 150px between elements
4. Vertical centering within lanes
5. Gateway branches: fan out vertically
6. Merge points: converge paths back

SHAPE DIMENSIONS:
- startEvent/endEvent: width=36, height=36
- userTask/serviceTask: width=100, height=80
- exclusiveGateway/parallelGateway: width=50, height=50
- Lane headers: width=30 (vertical text area)

EDGE WAYPOINTS:
- Horizontal connections: 2 waypoints (source right, target left)
- Vertical detours: 4 waypoints (around obstacles)
- Gateway branches: 3+ waypoints for routing

COORDINATE FORMULA:
- Element x = 152 + (column * 150)
- Element y = lane_y + (lane_height / 2) - (element_height / 2)

OUTPUT: BPMN XML with calculated coordinates for all shapes and edges.
"""

ARABIC_SUPPORT_PROMPT = """
The input is in Arabic. Generate BPMN with:
- Arabic task names and labels (e.g., name="تقديم الطلب")
- Arabic lane names (e.g., name="العميل")
- Arabic gateway labels
- Keep XML structure in English (element names, attributes, IDs)
- Use English IDs (e.g., Task_1, Gateway_1)
- Ensure proper UTF-8 encoding

EXAMPLE:
<bpmn:userTask id="Task_1" name="مراجعة الطلب">
<bpmn:lane id="Lane_1" name="قسم المبيعات">
"""


def create_llm(temperature=0.1, timeout=60, max_retries=2):
    """Factory function to create LLM instance based on Config.MODEL_NAME"""
    model_config = Config.get_current_model_config()
    provider = model_config["provider"]
    model_id = model_config["model_id"]

    if provider == "openai":
        if ChatOpenAI is None:
            raise ImportError("langchain-openai not installed. Run: pip install langchain-openai")
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries
        )
    elif provider == "anthropic":
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        return ChatAnthropic(
            model=model_id,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries
        )
    elif provider == "google":
        if ChatGoogleGenerativeAI is None:
            raise ImportError("langchain-google-genai not installed. Run: pip install langchain-google-genai")
        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


class BPMNAgents:
    """
    Enhanced BPMN Agents with 13 specialized agents:
    1. Generator - Creates initial BPMN
    2. Validator - Validates syntax
    3. Fixer - Fixes errors
    4. Visualizer - Adds diagram elements
    5. Camunda Optimizer - Camunda compatibility
    6. Deployment - Deploys to Camunda
    7. Improver - Fixes deployment errors
    8. Reviewer - Requirements check
    9. Process Analyzer - Bottleneck analysis
    10. Syntax Validator - XML syntax check
    11. Lane Designer (NEW) - Designs swim lanes
    12. Edge Validator (NEW) - Validates edges/flows
    13. Diagram Layouter (NEW) - Calculates coordinates
    """

    def __init__(self, session_memory: SessionMemory):
        self.session_memory = session_memory
        self.llm = create_llm(temperature=0.1)

    def create_generator_agent(self):
        """Creates BPMN from process description with enhanced prompts"""
        # Check if input is Arabic
        is_arabic = False
        if self.session_memory.original_description:
            is_arabic = detect_language(self.session_memory.original_description) == 'ar'

        backstory = GENERATOR_BACKSTORY
        if is_arabic:
            backstory += "\n\n" + ARABIC_SUPPORT_PROMPT

        return Agent(
            role="BPMN Process Generator",
            goal="Generate complete, valid BPMN 2.0 XML with all edges, shapes, and proper structure",
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=create_llm(temperature=0.1, timeout=120, max_retries=3)
        )

    def create_validator_agent(self):
        """Validates BPMN XML syntax and structure"""
        return Agent(
            role="BPMN Validator",
            goal="Validate BPMN XML syntax and structure using BPMN 2.0 standards",
            backstory="""You are a BPMN validation expert who ensures XML structure is correct
            and follows BPMN 2.0 specification. You can identify:
            - XML syntax errors
            - Missing required elements
            - Invalid namespace declarations
            - Broken element references
            - Missing diagram elements
            Return specific error messages for any issues found.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def create_fixer_agent(self):
        """Fixes BPMN validation errors using session history"""
        return Agent(
            role="BPMN Fixer with Session Memory",
            goal="Fix BPMN validation errors using session history and context",
            backstory=f"""You are a BPMN repair specialist with access to all previous fix attempts.
            You learn from past failures and apply cumulative knowledge to solve complex issues.

            Current session context:
            Original Description: {self.session_memory.original_description}
            {self.session_memory.get_fix_history_summary()}

            FIXING STRATEGY:
            1. Parse the error message carefully
            2. Identify the root cause
            3. Apply targeted fix (don't rewrite entire XML)
            4. Verify fix addresses the error
            5. Ensure no new errors introduced

            You must avoid repeating failed approaches and build upon previous learnings.""",
            verbose=True,
            allow_delegation=False,
            llm=create_llm(temperature=0.2)
        )

    def create_improver_agent(self):
        """Fixes BPMN for Camunda deployment"""
        return Agent(
            role="Camunda Deployment Improver",
            goal="Fix BPMN models that fail Camunda deployment validation",
            backstory="""You are a Camunda BPM expert who understands engine requirements.
            You can fix issues like:
            - Missing process IDs
            - Incorrect executable flags
            - Invalid element references
            - Missing history time to live
            - Engine-specific validation failures

            CAMUNDA REQUIREMENTS:
            - camunda:historyTimeToLive="P1D" on process element
            - isExecutable="true"
            - Valid element IDs (no spaces or special chars)
            - Proper namespace for Camunda extensions""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def create_reviewer_agent(self):
        """Reviews BPMN against original requirements"""
        return Agent(
            role="BPMN Process Reviewer",
            goal="Validate BPMN completeness against original requirements",
            backstory=f"""Process completeness reviewer. Check that:
            - All steps from description are represented
            - Decision logic matches requirements
            - Flow sequence is correct
            - No missing elements
            - Proper start and end events

            Original description to check against:
            {self.session_memory.original_description}

            Return: VERDICT: PASS or VERDICT: NO_PASS
            If NO_PASS, include FEEDBACK: with specific issues""",
            verbose=True,
            allow_delegation=False,
            llm=create_llm(temperature=0.1)
        )

    def create_visualizer_agent(self):
        """Adds diagram elements for visualization"""
        return Agent(
            role="BPMN Visualizer",
            goal="Add proper BPMN diagram elements for visualization",
            backstory="""BPMN visualization expert. Critical rules:
            - Keep process elements inside <bpmn:process>
            - Add <bpmndi:BPMNDiagram> AFTER </bpmn:process>
            - BPMNShape for EVERY flow element
            - BPMNEdge for EVERY sequenceFlow
            - Each shape needs dc:Bounds with x, y, width, height
            - Each edge needs di:waypoint elements (minimum 2)
            - Never mix process and diagram elements

            LAYOUT GUIDELINES:
            - Start from left (x=152)
            - Flow horizontally to the right
            - Space elements 150px apart
            - Center vertically in lanes""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def create_camunda_optimizer_agent(self):
        """Optimizes BPMN for Camunda engine"""
        return Agent(
            role="Camunda Optimizer",
            goal="Fix BPMN for Camunda engine compatibility",
            backstory="""Camunda deployment expert. Critical fixes:
            - Add xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
            - Add camunda:historyTimeToLive="P1D" to process element
            - Ensure isExecutable="true"
            - Add <bpmn:incoming> and <bpmn:outgoing> to all flow elements
            - Keep BPMNDiagram separate from process
            - Fix any XML structure violations
            - Ensure all IDs are valid (alphanumeric + underscore)

            Output deployment-ready XML only.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def create_deployment_agent(self):
        """Deploys BPMN to Camunda"""
        return Agent(
            role="Deployment Specialist",
            goal="Deploy BPMN to Camunda and handle errors",
            backstory="""Deployment expert. Actions:
            - Deploy to Camunda REST API
            - Parse deployment error responses
            - Identify specific issues
            - Coordinate fixes with optimizer
            - Retry deployment until successful""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def create_syntax_validator_agent(self):
        """Validates XML syntax"""
        return Agent(
            role="BPMN Syntax Validator",
            goal="Validate BPMN XML syntax thoroughly",
            backstory="""XML and BPMN syntax expert.
            Check:
            - XML well-formedness (proper tags, nesting)
            - BPMN 2.0 namespace declarations
            - Required attributes on elements
            - ID uniqueness
            - Reference validity (sourceRef, targetRef)

            Return specific syntax errors with line context.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def create_process_analyzer_agent(self):
        """Analyzes process for optimization"""
        return Agent(
            role="Process Analyzer",
            goal="Analyze process for optimization opportunities",
            backstory="""Process analysis expert.
            Identify:
            - Potential bottlenecks
            - Redundant steps
            - Missing decision points
            - Parallelization opportunities
            - Process improvement suggestions

            Output structured analysis with recommendations.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    # NEW AGENTS

    def create_lane_designer_agent(self):
        """NEW: Designs swim lanes based on actors"""
        return Agent(
            role="BPMN Lane Designer",
            goal="Design swim lanes based on actors/departments in the process",
            backstory=LANE_DESIGNER_BACKSTORY,
            verbose=True,
            allow_delegation=False,
            llm=create_llm(temperature=0.2)
        )

    def create_edge_validator_agent(self):
        """NEW: Validates all edges and flows"""
        return Agent(
            role="BPMN Edge Validator",
            goal="Ensure every sequenceFlow has a matching BPMNEdge with waypoints",
            backstory=EDGE_VALIDATOR_BACKSTORY,
            verbose=True,
            allow_delegation=False,
            llm=create_llm(temperature=0.1)
        )

    def create_diagram_layouter_agent(self):
        """NEW: Calculates coordinates for shapes and edges"""
        return Agent(
            role="BPMN Diagram Layouter",
            goal="Calculate optimal coordinates for all BPMN shapes and edges",
            backstory=DIAGRAM_LAYOUTER_BACKSTORY,
            verbose=True,
            allow_delegation=False,
            llm=create_llm(temperature=0.1)
        )


class BPMNTasks:
    """Task definitions for BPMN agents"""

    def __init__(self, session_memory: SessionMemory):
        self.session_memory = session_memory

    def create_generation_task(self, description: str, agent):
        """Create BPMN generation task with enhanced instructions"""
        # Check if Arabic
        is_arabic = detect_language(description) == 'ar'

        # Truncate very long descriptions
        if len(description) > 2000:
            description = description[:2000] + "... [Focus on main workflow steps]"

        arabic_instruction = ""
        if is_arabic:
            arabic_instruction = """
            IMPORTANT: Input is in Arabic. Use Arabic text for:
            - Task names (name attribute)
            - Lane names
            - Gateway labels
            Keep element IDs in English (e.g., Task_1, Gateway_1).
            """

        return Task(
            description=f"""Create complete BPMN 2.0 XML for this process:

            {description}

            {arabic_instruction}

            REQUIREMENTS:
            1. Create proper flow: Start Event → Tasks → Gateways → End Event
            2. Add swim lanes for different actors/departments
            3. Connect ALL elements with sequenceFlow
            4. Include COMPLETE diagram section with:
               - BPMNShape for every element (with dc:Bounds)
               - BPMNEdge for every sequenceFlow (with di:waypoint)
            5. Use proper namespaces and isExecutable="true"

            OUTPUT: Raw BPMN XML only. No markdown. No explanations.""",
            agent=agent,
            expected_output="Complete BPMN 2.0 XML with process and diagram sections",
            max_execution_time=180
        )

    def create_validation_task(self, bpmn_xml: str, agent):
        """Create validation task"""
        return Task(
            description=f"""
            Validate this BPMN XML for syntax and structural correctness:

            {bpmn_xml}

            Check for:
            1. Valid XML syntax
            2. Proper BPMN 2.0 namespace declarations
            3. Required process elements and attributes
            4. Proper element nesting and relationships
            5. Valid sequence flow connections (sourceRef, targetRef)
            6. Missing or invalid IDs
            7. BPMNShape for every flow element
            8. BPMNEdge for every sequenceFlow

            Return either "VALID" or detailed error description.
            """,
            agent=agent,
            expected_output="Validation result: VALID or detailed error message"
        )

    def create_fixing_task(self, bpmn_xml: str, error_message: str, agent):
        """Create fixing task"""
        return Task(
            description=f"""Fix this BPMN error: {error_message}

            Current XML:
            {bpmn_xml}

            FIXING INSTRUCTIONS:
            1. Parse the error carefully
            2. Make targeted fix (minimal changes)
            3. Preserve existing structure
            4. Ensure fix resolves the error

            Output format:
            FIXED_XML: <corrected XML here>
            FIX_DESCRIPTION: <what was fixed>""",
            agent=agent,
            expected_output="Fixed BPMN XML with description"
        )

    def create_visualization_task(self, bpmn_xml: str, agent):
        """Create visualization task"""
        return Task(
            description=f"""Add proper BPMN diagram structure:
            {bpmn_xml}

            RULES:
            - Process elements stay in <bpmn:process>
            - Add <bpmndi:BPMNDiagram> AFTER </bpmn:process>
            - BPMNShape/BPMNEdge ONLY in BPMNPlane
            - No diagram elements inside process
            - Every element needs a shape with bounds
            - Every flow needs an edge with waypoints

            COORDINATE GUIDELINES:
            - Start: x=152, y=100
            - Horizontal spacing: 150px
            - Task: width=100, height=80
            - Event: width=36, height=36
            - Gateway: width=50, height=50

            Output correct XML structure only.""",
            agent=agent,
            expected_output="Properly structured BPMN XML with diagram"
        )

    def create_camunda_optimization_task(self, bpmn_xml: str, agent):
        """Create Camunda optimization task"""
        return Task(
            description=f"""Fix BPMN for Camunda deployment:
            {bpmn_xml}

            Critical fixes:
            - Add camunda namespace if missing
            - Add camunda:historyTimeToLive="P1D" to process element
            - Add <bpmn:incoming> and <bpmn:outgoing> to all flow elements
            - Ensure isExecutable="true"
            - Keep BPMNDiagram separate from process
            - Fix any XML structure violations

            Output deployment-ready XML only.""",
            agent=agent,
            expected_output="Camunda deployment-ready BPMN XML"
        )

    def create_deployment_task(self, bpmn_xml: str, agent):
        """Create deployment task"""
        return Task(
            description=f"""Deploy to Camunda:
            {bpmn_xml}

            Use REST API.
            Handle deployment errors.
            Return deployment status.""",
            agent=agent,
            expected_output="Deployment result"
        )

    def create_improvement_task(self, bpmn_xml: str, camunda_error: str, agent):
        """Create improvement task for deployment errors"""
        return Task(
            description=f"""
            Fix this BPMN XML to resolve Camunda deployment error:

            BPMN XML:
            {bpmn_xml}

            Camunda Error:
            {camunda_error}

            Previous attempts:
            {len(self.session_memory.camunda_deployment_attempts)} attempts made

            Fix the XML to meet Camunda engine requirements.
            Output only the corrected XML.
            """,
            agent=agent,
            expected_output="Camunda-compatible BPMN XML"
        )

    def create_review_task(self, bpmn_xml: str, agent):
        """Create review task"""
        return Task(
            description=f"""Review BPMN against original requirements:

            Original Description:
            {self.session_memory.original_description}

            Generated BPMN:
            {bpmn_xml}

            Check:
            - All steps from description are present
            - Logic and flow are correct
            - No missing elements
            - Proper connections

            Return:
            VERDICT: PASS or VERDICT: NO_PASS
            FEEDBACK: Specific issues if NO_PASS""",
            agent=agent,
            expected_output="PASS/NO_PASS verdict with feedback"
        )

    def create_lane_design_task(self, description: str, agent):
        """NEW: Create lane design task"""
        return Task(
            description=f"""Analyze this process description and design swim lanes:

            {description}

            INSTRUCTIONS:
            1. Identify all actors/departments/roles
            2. Create a lane for each actor
            3. Assign tasks to appropriate lanes
            4. Plan cross-lane interactions

            Output lane structure as part of BPMN XML.""",
            agent=agent,
            expected_output="BPMN XML with designed lanes"
        )

    def create_edge_validation_task(self, bpmn_xml: str, agent):
        """NEW: Create edge validation task"""
        return Task(
            description=f"""Validate and fix edges in this BPMN:

            {bpmn_xml}

            CHECK:
            1. Count all sequenceFlow elements
            2. Count all BPMNEdge elements
            3. Verify each flow has a corresponding edge
            4. Verify each edge has >= 2 waypoints
            5. Add missing edges with calculated waypoints

            Output corrected BPMN XML.""",
            agent=agent,
            expected_output="BPMN XML with all edges present"
        )

    def create_layout_task(self, bpmn_xml: str, agent):
        """NEW: Create layout calculation task"""
        return Task(
            description=f"""Calculate layout coordinates for this BPMN:

            {bpmn_xml}

            LAYOUT RULES:
            - Start event: x=152
            - Horizontal flow: left to right
            - 150px spacing between elements
            - Center elements vertically in lanes
            - Calculate edge waypoints

            Output BPMN XML with all coordinates.""",
            agent=agent,
            expected_output="BPMN XML with calculated layout"
        )


def add_camunda_namespace(bpmn_xml: str) -> str:
    """Add Camunda namespace to BPMN XML if missing"""
    if 'xmlns:camunda=' not in bpmn_xml:
        bpmn_xml = bpmn_xml.replace(
            'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"',
            'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:camunda="http://camunda.org/schema/1.0/bpmn"'
        )
    return bpmn_xml


def ensure_process_executable(bpmn_xml: str) -> str:
    """Ensure process has isExecutable='true'"""
    if 'isExecutable="true"' not in bpmn_xml:
        bpmn_xml = re.sub(
            r'<bpmn:process\s+id="([^"]*)"',
            r'<bpmn:process id="\1" isExecutable="true"',
            bpmn_xml
        )
    return bpmn_xml


def add_history_time_to_live(bpmn_xml: str) -> str:
    """Add Camunda history time to live if missing"""
    if 'camunda:historyTimeToLive' not in bpmn_xml:
        # Add to process element
        bpmn_xml = re.sub(
            r'(<bpmn:process[^>]*)(>)',
            r'\1 camunda:historyTimeToLive="P1D"\2',
            bpmn_xml,
            count=1
        )
    return bpmn_xml


def deploy_to_camunda(bpmn_xml: str, process_name: str = "my-process") -> dict:
    """Deploy BPMN XML to Camunda and return deployment response"""
    try:
        # Optimize BPMN for Camunda
        optimized_xml = add_camunda_namespace(bpmn_xml)
        optimized_xml = ensure_process_executable(optimized_xml)
        optimized_xml = add_history_time_to_live(optimized_xml)

        # Save BPMN to temporary file
        temp_file = f"/tmp/{process_name}.bpmn"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(optimized_xml)

        # Deploy to Camunda
        url = f"{Config.CAMUNDA_URL}/engine-rest/deployment/create"
        files = {
            f"{process_name}.bpmn": open(temp_file, 'rb')
        }
        data = {
            "deployment-name": process_name
        }

        response = requests.post(
            url,
            files=files,
            data=data,
            auth=(Config.CAMUNDA_USERNAME, Config.CAMUNDA_PASSWORD),
            timeout=30
        )

        files[f"{process_name}.bpmn"].close()

        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text,
            "error": None if response.status_code == 200 else response.text
        }

    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "response": None,
            "error": str(e)
        }


def validate_bpmn_xml(bpmn_xml: str) -> dict:
    """Validate BPMN XML using comprehensive validator"""
    result = validate_bpmn_comprehensive(bpmn_xml)

    # Convert to simple format for backward compatibility
    if result['valid']:
        return {"valid": True, "error": None}
    else:
        # Return first error for simple API
        errors = result.get('errors', [])
        error_msg = errors[0] if errors else "Validation failed"
        return {"valid": False, "error": error_msg}
