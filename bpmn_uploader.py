"""
BPMN Upload and Validation Module
Handles uploading, validating, and viewing existing BPMN files
"""

from typing import Dict, Any, Optional, BinaryIO
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from validation import BPMNValidator, validate_bpmn_comprehensive, get_validation_summary


@dataclass
class UploadResult:
    """Result of processing an uploaded BPMN file"""
    filename: str
    content: str
    file_size: int
    validation: Dict[str, Any]
    can_view: bool
    can_deploy: bool
    process_id: Optional[str] = None
    process_name: Optional[str] = None
    error: Optional[str] = None


class BPMNUploader:
    """
    Handle BPMN file uploads with validation

    Features:
    - Parse uploaded BPMN/XML files
    - Comprehensive validation
    - Extract process metadata
    - Prepare for viewing and deployment
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.bpmn', '.xml']

    # Maximum file size (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024

    def __init__(self):
        self.validator = BPMNValidator()

    def process_upload(self, uploaded_file: BinaryIO, filename: str) -> UploadResult:
        """
        Process an uploaded BPMN file

        Args:
            uploaded_file: File-like object with BPMN content
            filename: Original filename

        Returns:
            UploadResult with validation and metadata
        """
        try:
            # Read file content
            content = uploaded_file.read()
            file_size = len(content)

            # Check file size
            if file_size > self.MAX_FILE_SIZE:
                return UploadResult(
                    filename=filename,
                    content="",
                    file_size=file_size,
                    validation={'valid': False, 'errors': ['File too large (max 5MB)']},
                    can_view=False,
                    can_deploy=False,
                    error=f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum (5MB)"
                )

            # Decode content
            if isinstance(content, bytes):
                content = content.decode('utf-8')

            # Validate BPMN
            validation = self.validator.validate_comprehensive(content)

            # Extract metadata
            process_id, process_name = self._extract_process_metadata(content)

            # Determine capabilities
            can_view = validation['valid'] or len(validation.get('errors', [])) == 0
            can_deploy = validation['valid']

            return UploadResult(
                filename=filename,
                content=content,
                file_size=file_size,
                validation=validation,
                can_view=can_view,
                can_deploy=can_deploy,
                process_id=process_id,
                process_name=process_name
            )

        except UnicodeDecodeError as e:
            return UploadResult(
                filename=filename,
                content="",
                file_size=0,
                validation={'valid': False, 'errors': ['Invalid file encoding (must be UTF-8)']},
                can_view=False,
                can_deploy=False,
                error=f"Encoding error: {str(e)}"
            )
        except Exception as e:
            return UploadResult(
                filename=filename,
                content="",
                file_size=0,
                validation={'valid': False, 'errors': [str(e)]},
                can_view=False,
                can_deploy=False,
                error=str(e)
            )

    def _extract_process_metadata(self, bpmn_xml: str) -> tuple:
        """
        Extract process ID and name from BPMN XML

        Args:
            bpmn_xml: BPMN XML content

        Returns:
            Tuple of (process_id, process_name)
        """
        try:
            root = ET.fromstring(bpmn_xml)
            ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

            # Find process element
            process = root.find('.//{%s}process' % ns['bpmn'])

            if process is not None:
                process_id = process.get('id')
                process_name = process.get('name', process_id)
                return process_id, process_name

            return None, None

        except Exception:
            return None, None

    def validate_file_extension(self, filename: str) -> bool:
        """
        Check if file has valid extension

        Args:
            filename: Filename to check

        Returns:
            True if extension is supported
        """
        lower_name = filename.lower()
        return any(lower_name.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)

    def get_file_info(self, content: str) -> Dict[str, Any]:
        """
        Get detailed information about BPMN content

        Args:
            content: BPMN XML content

        Returns:
            Dictionary with file analysis
        """
        info = {
            'content_length': len(content),
            'line_count': content.count('\n') + 1,
            'has_diagram': False,
            'namespaces': [],
            'element_counts': {}
        }

        try:
            root = ET.fromstring(content)
            ns = {
                'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
                'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI'
            }

            # Check for diagram
            diagram = root.find('.//{%s}BPMNDiagram' % ns['bpmndi'])
            info['has_diagram'] = diagram is not None

            # Extract namespace prefixes
            for key, value in root.attrib.items():
                if key.startswith('{') or 'xmlns' in key:
                    info['namespaces'].append(value if 'xmlns' not in key else key.split('}')[-1])

            # Count elements
            element_types = [
                'startEvent', 'endEvent', 'userTask', 'serviceTask', 'task',
                'exclusiveGateway', 'parallelGateway', 'sequenceFlow', 'lane'
            ]

            for elem_type in element_types:
                count = len(root.findall('.//{%s}%s' % (ns['bpmn'], elem_type)))
                if count > 0:
                    info['element_counts'][elem_type] = count

        except Exception:
            pass

        return info


def create_upload_summary(result: UploadResult) -> str:
    """
    Create a human-readable summary of upload result

    Args:
        result: UploadResult from processing

    Returns:
        Formatted summary string
    """
    lines = [
        "=" * 50,
        "BPMN FILE UPLOAD SUMMARY",
        "=" * 50,
        "",
        f"Filename:     {result.filename}",
        f"File Size:    {result.file_size / 1024:.2f} KB",
        ""
    ]

    if result.process_id:
        lines.extend([
            f"Process ID:   {result.process_id}",
            f"Process Name: {result.process_name or 'N/A'}",
            ""
        ])

    # Validation status
    if result.validation.get('valid'):
        lines.append("Validation:   PASSED")
    else:
        lines.append("Validation:   FAILED")
        for error in result.validation.get('errors', []):
            lines.append(f"  - {error}")

    lines.append("")

    # Warnings
    warnings = result.validation.get('warnings', [])
    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        for warning in warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    # Capabilities
    lines.extend([
        "Capabilities:",
        f"  View in Browser:  {'Yes' if result.can_view else 'No'}",
        f"  Deploy to Camunda: {'Yes' if result.can_deploy else 'No'}",
    ])

    # Statistics
    stats = result.validation.get('stats', {})
    if stats:
        lines.extend([
            "",
            "Model Statistics:",
            f"  Tasks:          {stats.get('total_tasks', 0)}",
            f"  Gateways:       {stats.get('total_gateways', 0)}",
            f"  Sequence Flows: {stats.get('sequence_flows', 0)}",
            f"  Swim Lanes:     {stats.get('lanes', 0)}"
        ])

    lines.extend([
        "",
        "=" * 50
    ])

    return "\n".join(lines)


class BPMNFileComparator:
    """
    Compare two BPMN files for differences
    Useful for comparing uploaded file with generated version
    """

    def __init__(self):
        self.validator = BPMNValidator()

    def compare(self, bpmn1: str, bpmn2: str) -> Dict[str, Any]:
        """
        Compare two BPMN XML files

        Args:
            bpmn1: First BPMN XML content
            bpmn2: Second BPMN XML content

        Returns:
            Dictionary with comparison results
        """
        result = {
            'identical': bpmn1 == bpmn2,
            'file1_valid': False,
            'file2_valid': False,
            'differences': []
        }

        # Validate both files
        val1 = self.validator.validate_comprehensive(bpmn1)
        val2 = self.validator.validate_comprehensive(bpmn2)

        result['file1_valid'] = val1['valid']
        result['file2_valid'] = val2['valid']
        result['file1_stats'] = val1.get('stats', {})
        result['file2_stats'] = val2.get('stats', {})

        # Compare statistics
        stats1 = val1.get('stats', {})
        stats2 = val2.get('stats', {})

        for key in set(stats1.keys()) | set(stats2.keys()):
            v1 = stats1.get(key, 0)
            v2 = stats2.get(key, 0)
            if v1 != v2:
                result['differences'].append({
                    'metric': key,
                    'file1': v1,
                    'file2': v2,
                    'delta': v2 - v1
                })

        return result
