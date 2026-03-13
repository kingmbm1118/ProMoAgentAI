"""
Batch Processing Module for ProMoAgentAI
Processes multiple BPMN descriptions and outputs ZIP or local files
"""

import os
import zipfile
import io
import tempfile
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
import re


@dataclass
class BatchProcessResult:
    """Result for a single batch item"""
    index: int
    description: str
    success: bool
    bpmn_xml: str = ""
    filename: str = ""
    error: str = ""
    validation_result: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0


@dataclass
class BatchResults:
    """Aggregated results for batch processing"""
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: List[BatchProcessResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100


class BatchProcessor:
    """
    Process multiple BPMN descriptions in batch mode

    Supports:
    - Processing multiple descriptions from text file
    - ZIP download of all generated BPMN files
    - Local directory save
    - Progress tracking with callbacks
    """

    def __init__(self, orchestrator):
        """
        Initialize batch processor

        Args:
            orchestrator: BPMNOrchestrator instance for BPMN generation
        """
        self.orchestrator = orchestrator

    def parse_descriptions(self, content: str) -> List[str]:
        """
        Parse descriptions from text content

        Supports multiple formats:
        - One description per line
        - Descriptions separated by blank lines
        - Numbered descriptions (1. Description)

        Args:
            content: Raw text content with descriptions

        Returns:
            List of individual descriptions
        """
        descriptions = []

        # Check if content uses numbered format
        numbered_pattern = re.compile(r'^\d+\.\s*(.+)$', re.MULTILINE)
        numbered_matches = numbered_pattern.findall(content)

        if numbered_matches:
            descriptions = [match.strip() for match in numbered_matches if match.strip()]
        else:
            # Split by double newlines (paragraph-based)
            paragraphs = content.split('\n\n')

            if len(paragraphs) > 1:
                descriptions = [p.strip() for p in paragraphs if p.strip()]
            else:
                # Fall back to line-by-line
                lines = content.split('\n')
                descriptions = [line.strip() for line in lines if line.strip()]

        return descriptions

    def generate_filename(self, description: str, index: int) -> str:
        """
        Generate a filename from description

        Args:
            description: Process description
            index: Item index (1-based)

        Returns:
            Safe filename string
        """
        # Extract first few words for filename
        words = description.split()[:5]
        name_part = '_'.join(words)

        # Remove special characters
        name_part = re.sub(r'[^\w\s-]', '', name_part)
        name_part = re.sub(r'[-\s]+', '_', name_part)

        # Truncate if too long
        if len(name_part) > 50:
            name_part = name_part[:50]

        return f"process_{index:03d}_{name_part}.bpmn"

    def process_batch(
        self,
        descriptions: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> BatchResults:
        """
        Process multiple descriptions

        Args:
            descriptions: List of process descriptions
            progress_callback: Optional callback(current, total, status)

        Returns:
            BatchResults with all processing results
        """
        import time

        results = BatchResults(
            total=len(descriptions),
            started_at=datetime.now()
        )

        for i, description in enumerate(descriptions):
            start_time = time.time()

            if progress_callback:
                progress_callback(i + 1, len(descriptions), f"Processing: {description[:50]}...")

            try:
                # Reset session for each description
                self.orchestrator.reset_session()

                # Execute full workflow
                workflow_result = self.orchestrator.execute_full_workflow(description)

                processing_time = time.time() - start_time

                if workflow_result['success'] or workflow_result.get('bpmn_xml'):
                    result = BatchProcessResult(
                        index=i + 1,
                        description=description,
                        success=True,
                        bpmn_xml=workflow_result['bpmn_xml'],
                        filename=self.generate_filename(description, i + 1),
                        processing_time=processing_time
                    )
                    results.successful += 1
                else:
                    result = BatchProcessResult(
                        index=i + 1,
                        description=description,
                        success=False,
                        error=workflow_result.get('final_status', 'Unknown error'),
                        processing_time=processing_time
                    )
                    results.failed += 1

            except Exception as e:
                processing_time = time.time() - start_time
                result = BatchProcessResult(
                    index=i + 1,
                    description=description,
                    success=False,
                    error=str(e),
                    processing_time=processing_time
                )
                results.failed += 1

            results.results.append(result)

        results.completed_at = datetime.now()
        return results

    def create_zip(self, results: BatchResults) -> bytes:
        """
        Create ZIP file from batch results

        Args:
            results: BatchResults with generated BPMN files

        Returns:
            ZIP file content as bytes
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add successful BPMN files
            for result in results.results:
                if result.success and result.bpmn_xml:
                    zip_file.writestr(result.filename, result.bpmn_xml)

            # Add summary report
            summary = self._generate_summary_report(results)
            zip_file.writestr('batch_report.txt', summary)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def save_to_directory(self, results: BatchResults, output_dir: str) -> Dict[str, str]:
        """
        Save batch results to local directory

        Args:
            results: BatchResults with generated BPMN files
            output_dir: Target directory path

        Returns:
            Dict mapping filenames to full paths
        """
        os.makedirs(output_dir, exist_ok=True)

        saved_files = {}

        for result in results.results:
            if result.success and result.bpmn_xml:
                filepath = os.path.join(output_dir, result.filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(result.bpmn_xml)
                saved_files[result.filename] = filepath

        # Save summary report
        summary = self._generate_summary_report(results)
        report_path = os.path.join(output_dir, 'batch_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        saved_files['batch_report.txt'] = report_path

        return saved_files

    def _generate_summary_report(self, results: BatchResults) -> str:
        """Generate batch processing summary report"""
        lines = [
            "=" * 60,
            "BATCH PROCESSING REPORT",
            "=" * 60,
            "",
            f"Started:    {results.started_at.strftime('%Y-%m-%d %H:%M:%S') if results.started_at else 'N/A'}",
            f"Completed:  {results.completed_at.strftime('%Y-%m-%d %H:%M:%S') if results.completed_at else 'N/A'}",
            "",
            f"Total Processes:      {results.total}",
            f"Successful:           {results.successful}",
            f"Failed:               {results.failed}",
            f"Success Rate:         {results.success_rate:.1f}%",
            "",
            "-" * 60,
            "INDIVIDUAL RESULTS",
            "-" * 60,
            ""
        ]

        for result in results.results:
            status = "SUCCESS" if result.success else "FAILED"
            lines.append(f"[{result.index}] {status}")
            lines.append(f"    Description: {result.description[:80]}...")

            if result.success:
                lines.append(f"    Output File: {result.filename}")
            else:
                lines.append(f"    Error: {result.error}")

            lines.append(f"    Processing Time: {result.processing_time:.2f}s")
            lines.append("")

        lines.append("=" * 60)
        lines.append("END OF REPORT")
        lines.append("=" * 60)

        return "\n".join(lines)


class AsyncBatchProcessor:
    """
    Async version of batch processor for non-blocking UI updates
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.batch_processor = BatchProcessor(orchestrator)
        self._is_running = False
        self._should_cancel = False
        self._current_results: Optional[BatchResults] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def cancel(self):
        """Request cancellation of running batch"""
        self._should_cancel = True

    def process_batch_async(
        self,
        descriptions: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> BatchResults:
        """
        Process batch with cancellation support

        Args:
            descriptions: List of process descriptions
            progress_callback: Optional callback(current, total, status)

        Returns:
            BatchResults (may be partial if cancelled)
        """
        import time

        self._is_running = True
        self._should_cancel = False

        results = BatchResults(
            total=len(descriptions),
            started_at=datetime.now()
        )
        self._current_results = results

        for i, description in enumerate(descriptions):
            # Check for cancellation
            if self._should_cancel:
                break

            start_time = time.time()

            if progress_callback:
                progress_callback(i + 1, len(descriptions), f"Processing: {description[:50]}...")

            try:
                self.orchestrator.reset_session()
                workflow_result = self.orchestrator.execute_full_workflow(description)
                processing_time = time.time() - start_time

                if workflow_result['success'] or workflow_result.get('bpmn_xml'):
                    result = BatchProcessResult(
                        index=i + 1,
                        description=description,
                        success=True,
                        bpmn_xml=workflow_result['bpmn_xml'],
                        filename=self.batch_processor.generate_filename(description, i + 1),
                        processing_time=processing_time
                    )
                    results.successful += 1
                else:
                    result = BatchProcessResult(
                        index=i + 1,
                        description=description,
                        success=False,
                        error=workflow_result.get('final_status', 'Unknown error'),
                        processing_time=processing_time
                    )
                    results.failed += 1

            except Exception as e:
                processing_time = time.time() - start_time
                result = BatchProcessResult(
                    index=i + 1,
                    description=description,
                    success=False,
                    error=str(e),
                    processing_time=processing_time
                )
                results.failed += 1

            results.results.append(result)

        results.completed_at = datetime.now()
        self._is_running = False
        self._current_results = results

        return results
