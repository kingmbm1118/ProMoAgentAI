"""
Comprehensive BPMN 2.0 Validation Module
Validates BPMN XML structure, edges, flows, and diagram elements
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Set
import re


class BPMNValidator:
    """Comprehensive BPMN 2.0 validator with full structure checking"""

    # BPMN 2.0 Namespaces
    NAMESPACES = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc': 'http://www.omg.org/spec/DD/20100524/DC',
        'di': 'http://www.omg.org/spec/DD/20100524/DI',
        'camunda': 'http://camunda.org/schema/1.0/bpmn'
    }

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, int] = {}

    def validate_comprehensive(self, bpmn_xml: str) -> Dict[str, Any]:
        """
        Perform comprehensive BPMN 2.0 validation

        Returns:
            dict with 'valid', 'errors', 'warnings', and 'stats' keys
        """
        self.errors = []
        self.warnings = []
        self.stats = {}

        # Step 1: XML Parse Check
        try:
            root = ET.fromstring(bpmn_xml)
        except ET.ParseError as e:
            return {
                'valid': False,
                'errors': [f"XML Parse Error: {str(e)}"],
                'warnings': [],
                'stats': {}
            }

        # Step 2: Namespace validation
        self._validate_namespaces(bpmn_xml, root)

        # Step 3: Process element validation
        process = self._validate_process(root)

        if process is not None:
            # Step 4: Flow elements validation
            self._validate_flow_elements(root, process)

            # Step 5: Sequence flows validation
            self._validate_sequence_flows(root)

            # Step 6: Diagram validation (shapes and edges)
            self._validate_diagram(root)

            # Step 7: Lane validation (if present)
            self._validate_lanes(root, process)

            # Step 8: Gateway validation
            self._validate_gateways(root)

        # Collect statistics
        self._collect_stats(root)

        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.stats
        }

    def _validate_namespaces(self, bpmn_xml: str, root: ET.Element) -> None:
        """Validate required BPMN namespaces are present"""
        required_ns = [
            ('bpmn', 'http://www.omg.org/spec/BPMN/20100524/MODEL'),
            ('bpmndi', 'http://www.omg.org/spec/BPMN/20100524/DI'),
        ]

        for prefix, uri in required_ns:
            if uri not in bpmn_xml:
                self.errors.append(f"Missing required namespace: {prefix} ({uri})")

        # Check root element is definitions
        if 'definitions' not in root.tag.lower():
            self.errors.append("Root element must be 'definitions'")

    def _validate_process(self, root: ET.Element) -> Optional[ET.Element]:
        """Validate process element exists and has required attributes"""
        ns = self.NAMESPACES

        # Try with namespace prefix
        process = root.find('.//bpmn:process', ns)

        # Try without prefix (some BPMN files use default namespace)
        if process is None:
            process = root.find('.//{%s}process' % ns['bpmn'])

        if process is None:
            self.errors.append("Missing bpmn:process element")
            return None

        # Check process ID
        process_id = process.get('id')
        if not process_id:
            self.errors.append("Process element missing 'id' attribute")

        # Check isExecutable
        is_executable = process.get('isExecutable')
        if is_executable != 'true':
            self.warnings.append("Process should have isExecutable='true' for deployment")

        return process

    def _validate_flow_elements(self, root: ET.Element, process: ET.Element) -> None:
        """Validate start events, end events, tasks, and gateways"""
        ns = self.NAMESPACES

        # Check for start event
        start_events = root.findall('.//{%s}startEvent' % ns['bpmn'])
        if not start_events:
            self.errors.append("Missing startEvent - process must have at least one start event")
        elif len(start_events) > 1:
            self.warnings.append(f"Multiple start events found ({len(start_events)}) - consider if this is intentional")

        # Check for end event
        end_events = root.findall('.//{%s}endEvent' % ns['bpmn'])
        if not end_events:
            self.errors.append("Missing endEvent - process must have at least one end event")

        # Check all flow elements have IDs
        flow_element_types = ['startEvent', 'endEvent', 'userTask', 'serviceTask',
                              'task', 'exclusiveGateway', 'parallelGateway',
                              'inclusiveGateway', 'eventBasedGateway']

        for element_type in flow_element_types:
            elements = root.findall('.//{%s}%s' % (ns['bpmn'], element_type))
            for elem in elements:
                if not elem.get('id'):
                    self.errors.append(f"{element_type} missing 'id' attribute")

    def _validate_sequence_flows(self, root: ET.Element) -> None:
        """Validate all sequence flows have proper source and target refs"""
        ns = self.NAMESPACES

        flows = root.findall('.//{%s}sequenceFlow' % ns['bpmn'])

        # Collect all element IDs for reference checking
        all_element_ids: Set[str] = set()
        for elem in root.iter():
            elem_id = elem.get('id')
            if elem_id:
                all_element_ids.add(elem_id)

        for flow in flows:
            flow_id = flow.get('id')
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')

            if not flow_id:
                self.errors.append("sequenceFlow missing 'id' attribute")

            if not source_ref:
                self.errors.append(f"sequenceFlow '{flow_id}' missing 'sourceRef' attribute")
            elif source_ref not in all_element_ids:
                self.errors.append(f"sequenceFlow '{flow_id}' has invalid sourceRef '{source_ref}' - element not found")

            if not target_ref:
                self.errors.append(f"sequenceFlow '{flow_id}' missing 'targetRef' attribute")
            elif target_ref not in all_element_ids:
                self.errors.append(f"sequenceFlow '{flow_id}' has invalid targetRef '{target_ref}' - element not found")

    def _validate_diagram(self, root: ET.Element) -> None:
        """Validate BPMNDiagram, BPMNShape, and BPMNEdge elements"""
        ns = self.NAMESPACES

        # Check for diagram element
        diagram = root.find('.//{%s}BPMNDiagram' % ns['bpmndi'])
        if diagram is None:
            self.warnings.append("Missing BPMNDiagram element - diagram may not render properly")
            return

        # Check for plane element
        plane = diagram.find('.//{%s}BPMNPlane' % ns['bpmndi'])
        if plane is None:
            self.warnings.append("Missing BPMNPlane element - diagram may not render properly")
            return

        # Collect all flow element IDs that need shapes
        flow_elements = set()
        flow_element_types = ['startEvent', 'endEvent', 'userTask', 'serviceTask',
                              'task', 'exclusiveGateway', 'parallelGateway',
                              'inclusiveGateway', 'eventBasedGateway', 'lane']

        for element_type in flow_element_types:
            for elem in root.findall('.//{%s}%s' % (ns['bpmn'], element_type)):
                elem_id = elem.get('id')
                if elem_id:
                    flow_elements.add(elem_id)

        # Collect all sequence flow IDs that need edges
        sequence_flows = set()
        for flow in root.findall('.//{%s}sequenceFlow' % ns['bpmn']):
            flow_id = flow.get('id')
            if flow_id:
                sequence_flows.add(flow_id)

        # Check shapes
        shapes = root.findall('.//{%s}BPMNShape' % ns['bpmndi'])
        shape_refs = set()

        for shape in shapes:
            bpmn_element = shape.get('bpmnElement')
            if bpmn_element:
                shape_refs.add(bpmn_element)

            # Check for bounds
            bounds = shape.find('{%s}Bounds' % ns['dc'])
            if bounds is None:
                self.errors.append(f"BPMNShape for '{bpmn_element}' missing dc:Bounds element")
            else:
                # Validate bounds attributes
                for attr in ['x', 'y', 'width', 'height']:
                    if bounds.get(attr) is None:
                        self.errors.append(f"BPMNShape for '{bpmn_element}' Bounds missing '{attr}' attribute")

        # Check for missing shapes (excluding lanes which are optional)
        missing_shapes = flow_elements - shape_refs
        if missing_shapes:
            # Only warn about non-lane elements
            for elem_id in missing_shapes:
                if not elem_id.lower().startswith('lane'):
                    self.warnings.append(f"Missing BPMNShape for element '{elem_id}'")

        # Check edges
        edges = root.findall('.//{%s}BPMNEdge' % ns['bpmndi'])
        edge_refs = set()

        for edge in edges:
            bpmn_element = edge.get('bpmnElement')
            if bpmn_element:
                edge_refs.add(bpmn_element)

            # Check for waypoints
            waypoints = edge.findall('{%s}waypoint' % ns['di'])
            if len(waypoints) < 2:
                self.errors.append(f"BPMNEdge for '{bpmn_element}' needs at least 2 waypoints (has {len(waypoints)})")

            # Validate waypoint attributes
            for i, wp in enumerate(waypoints):
                if wp.get('x') is None or wp.get('y') is None:
                    self.errors.append(f"BPMNEdge '{bpmn_element}' waypoint {i+1} missing x or y coordinate")

        # Check for missing edges
        missing_edges = sequence_flows - edge_refs
        if missing_edges:
            self.errors.append(f"Missing BPMNEdge for sequenceFlows: {missing_edges}")

    def _validate_lanes(self, root: ET.Element, process: ET.Element) -> None:
        """Validate swim lanes if present"""
        ns = self.NAMESPACES

        lane_set = process.find('{%s}laneSet' % ns['bpmn'])
        if lane_set is None:
            return  # Lanes are optional

        lanes = lane_set.findall('{%s}lane' % ns['bpmn'])

        for lane in lanes:
            lane_id = lane.get('id')
            if not lane_id:
                self.errors.append("Lane element missing 'id' attribute")

            lane_name = lane.get('name')
            if not lane_name:
                self.warnings.append(f"Lane '{lane_id}' missing 'name' attribute")

            # Check flowNodeRef elements
            flow_node_refs = lane.findall('{%s}flowNodeRef' % ns['bpmn'])
            if not flow_node_refs:
                self.warnings.append(f"Lane '{lane_id}' has no flowNodeRef elements")

    def _validate_gateways(self, root: ET.Element) -> None:
        """Validate gateway connections"""
        ns = self.NAMESPACES

        gateway_types = ['exclusiveGateway', 'parallelGateway', 'inclusiveGateway']

        for gateway_type in gateway_types:
            gateways = root.findall('.//{%s}%s' % (ns['bpmn'], gateway_type))

            for gateway in gateways:
                gateway_id = gateway.get('id')

                # Count incoming and outgoing flows
                incoming = gateway.findall('{%s}incoming' % ns['bpmn'])
                outgoing = gateway.findall('{%s}outgoing' % ns['bpmn'])

                # Gateways should have connections (either explicit or via sequenceFlow refs)
                if len(incoming) == 0 and len(outgoing) == 0:
                    # Check if connected via sequenceFlow
                    flows = root.findall('.//{%s}sequenceFlow' % ns['bpmn'])
                    has_incoming = any(f.get('targetRef') == gateway_id for f in flows)
                    has_outgoing = any(f.get('sourceRef') == gateway_id for f in flows)

                    if not has_incoming:
                        self.warnings.append(f"{gateway_type} '{gateway_id}' has no incoming connections")
                    if not has_outgoing:
                        self.warnings.append(f"{gateway_type} '{gateway_id}' has no outgoing connections")

    def _collect_stats(self, root: ET.Element) -> None:
        """Collect statistics about the BPMN model"""
        ns = self.NAMESPACES

        self.stats = {
            'start_events': len(root.findall('.//{%s}startEvent' % ns['bpmn'])),
            'end_events': len(root.findall('.//{%s}endEvent' % ns['bpmn'])),
            'user_tasks': len(root.findall('.//{%s}userTask' % ns['bpmn'])),
            'service_tasks': len(root.findall('.//{%s}serviceTask' % ns['bpmn'])),
            'tasks': len(root.findall('.//{%s}task' % ns['bpmn'])),
            'exclusive_gateways': len(root.findall('.//{%s}exclusiveGateway' % ns['bpmn'])),
            'parallel_gateways': len(root.findall('.//{%s}parallelGateway' % ns['bpmn'])),
            'sequence_flows': len(root.findall('.//{%s}sequenceFlow' % ns['bpmn'])),
            'lanes': len(root.findall('.//{%s}lane' % ns['bpmn'])),
            'shapes': len(root.findall('.//{%s}BPMNShape' % ns['bpmndi'])),
            'edges': len(root.findall('.//{%s}BPMNEdge' % ns['bpmndi']))
        }

        # Calculate total tasks
        self.stats['total_tasks'] = (self.stats['user_tasks'] +
                                     self.stats['service_tasks'] +
                                     self.stats['tasks'])

        # Calculate total gateways
        self.stats['total_gateways'] = (self.stats['exclusive_gateways'] +
                                        self.stats['parallel_gateways'])


def validate_bpmn_comprehensive(bpmn_xml: str) -> Dict[str, Any]:
    """
    Convenience function for comprehensive BPMN validation

    Args:
        bpmn_xml: BPMN XML string to validate

    Returns:
        dict with validation results
    """
    validator = BPMNValidator()
    return validator.validate_comprehensive(bpmn_xml)


def detect_language(text: str) -> str:
    """
    Detect if text contains Arabic characters

    Args:
        text: Input text to analyze

    Returns:
        'ar' for Arabic, 'en' for English/other
    """
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
    if arabic_pattern.search(text):
        return 'ar'
    return 'en'


def get_validation_summary(validation_result: Dict[str, Any]) -> str:
    """
    Generate a human-readable validation summary

    Args:
        validation_result: Result from validate_comprehensive()

    Returns:
        Formatted summary string
    """
    summary_lines = []

    if validation_result['valid']:
        summary_lines.append("BPMN Validation: PASSED")
    else:
        summary_lines.append("BPMN Validation: FAILED")

    summary_lines.append("")

    # Errors
    if validation_result['errors']:
        summary_lines.append(f"Errors ({len(validation_result['errors'])}):")
        for error in validation_result['errors']:
            summary_lines.append(f"  - {error}")
        summary_lines.append("")

    # Warnings
    if validation_result['warnings']:
        summary_lines.append(f"Warnings ({len(validation_result['warnings'])}):")
        for warning in validation_result['warnings']:
            summary_lines.append(f"  - {warning}")
        summary_lines.append("")

    # Statistics
    stats = validation_result.get('stats', {})
    if stats:
        summary_lines.append("Model Statistics:")
        summary_lines.append(f"  - Start Events: {stats.get('start_events', 0)}")
        summary_lines.append(f"  - End Events: {stats.get('end_events', 0)}")
        summary_lines.append(f"  - Total Tasks: {stats.get('total_tasks', 0)}")
        summary_lines.append(f"  - Total Gateways: {stats.get('total_gateways', 0)}")
        summary_lines.append(f"  - Sequence Flows: {stats.get('sequence_flows', 0)}")
        summary_lines.append(f"  - Swim Lanes: {stats.get('lanes', 0)}")
        summary_lines.append(f"  - Diagram Shapes: {stats.get('shapes', 0)}")
        summary_lines.append(f"  - Diagram Edges: {stats.get('edges', 0)}")

    return "\n".join(summary_lines)
