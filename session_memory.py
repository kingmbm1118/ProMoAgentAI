"""
Session Memory Module for ProMoAgentAI
Tracks fix attempts, deployment history, and validation results
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class FixAttempt:
    """Record of a single fix attempt"""
    iteration: int
    error_message: str
    fix_description: str
    bpmn_xml: str
    timestamp: datetime
    success: bool = False
    agent_used: str = ""


@dataclass
class ValidationResult:
    """Record of a validation attempt"""
    timestamp: datetime
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


@dataclass
class SessionMemory:
    """
    Maintains session state across the BPMN generation workflow

    Tracks:
    - Original process description
    - Fix attempts and their outcomes
    - Camunda deployment attempts
    - Validation results
    - Current BPMN XML state
    """

    # Process description
    original_description: str = ""
    detected_language: str = "en"

    # Fix tracking
    fix_attempts: List[FixAttempt] = field(default_factory=list)
    current_bpmn_xml: str = ""
    current_iteration: int = 0

    # Deployment tracking
    camunda_deployment_attempts: List[Dict[str, Any]] = field(default_factory=list)

    # Validation tracking
    validation_history: List[ValidationResult] = field(default_factory=list)

    # Status flags
    is_valid_bpmn: bool = False
    is_deployed_to_camunda: bool = False

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def add_fix_attempt(
        self,
        error_message: str,
        fix_description: str,
        bpmn_xml: str,
        success: bool = False,
        agent_used: str = ""
    ) -> None:
        """Record a fix attempt"""
        self.current_iteration += 1
        attempt = FixAttempt(
            iteration=self.current_iteration,
            error_message=error_message,
            fix_description=fix_description,
            bpmn_xml=bpmn_xml,
            timestamp=datetime.now(),
            success=success,
            agent_used=agent_used
        )
        self.fix_attempts.append(attempt)

        if success:
            self.current_bpmn_xml = bpmn_xml
            self.is_valid_bpmn = True

    def add_camunda_attempt(
        self,
        response_data: Dict[str, Any],
        success: bool = False
    ) -> None:
        """Record a Camunda deployment attempt"""
        attempt = {
            "timestamp": datetime.now(),
            "response": response_data,
            "success": success,
            "attempt_number": len(self.camunda_deployment_attempts) + 1
        }
        self.camunda_deployment_attempts.append(attempt)

        if success:
            self.is_deployed_to_camunda = True

    def add_validation_result(
        self,
        valid: bool,
        errors: List[str] = None,
        warnings: List[str] = None,
        stats: Dict[str, int] = None
    ) -> None:
        """Record a validation result"""
        result = ValidationResult(
            timestamp=datetime.now(),
            valid=valid,
            errors=errors or [],
            warnings=warnings or [],
            stats=stats or {}
        )
        self.validation_history.append(result)

        if valid:
            self.is_valid_bpmn = True

    def get_fix_history_summary(self) -> str:
        """Generate a summary of fix history for agent context"""
        if not self.fix_attempts:
            return "No previous fix attempts."

        summary_lines = [
            f"Fix History ({len(self.fix_attempts)} attempts):"
        ]

        for attempt in self.fix_attempts[-5:]:  # Last 5 attempts
            status = "SUCCESS" if attempt.success else "FAILED"
            error_preview = attempt.error_message[:100] + "..." if len(attempt.error_message) > 100 else attempt.error_message
            fix_preview = attempt.fix_description[:100] + "..." if len(attempt.fix_description) > 100 else attempt.fix_description

            summary_lines.append(
                f"Iteration {attempt.iteration} [{status}]: {error_preview}"
            )
            summary_lines.append(f"  Fix: {fix_preview}")
            summary_lines.append("")

        return "\n".join(summary_lines)

    def get_deployment_history_summary(self) -> str:
        """Generate a summary of deployment attempts"""
        if not self.camunda_deployment_attempts:
            return "No Camunda deployment attempts."

        summary_lines = [
            f"Deployment History ({len(self.camunda_deployment_attempts)} attempts):"
        ]

        for attempt in self.camunda_deployment_attempts[-3:]:  # Last 3 attempts
            status = "SUCCESS" if attempt["success"] else "FAILED"
            timestamp = attempt["timestamp"].strftime("%H:%M:%S")
            summary_lines.append(
                f"Attempt {attempt['attempt_number']} [{status}] at {timestamp}"
            )

            if not attempt["success"] and attempt["response"]:
                error = attempt["response"].get("error", "Unknown error")
                summary_lines.append(f"  Error: {error[:100]}...")

        return "\n".join(summary_lines)

    def get_last_error(self) -> Optional[str]:
        """Get the most recent error message"""
        if self.fix_attempts:
            return self.fix_attempts[-1].error_message
        return None

    def get_successful_fixes(self) -> List[FixAttempt]:
        """Get list of successful fixes"""
        return [a for a in self.fix_attempts if a.success]

    def get_failed_fixes(self) -> List[FixAttempt]:
        """Get list of failed fixes"""
        return [a for a in self.fix_attempts if not a.success]

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        duration = None
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return {
            "total_fix_attempts": len(self.fix_attempts),
            "successful_fixes": len(self.get_successful_fixes()),
            "failed_fixes": len(self.get_failed_fixes()),
            "deployment_attempts": len(self.camunda_deployment_attempts),
            "is_valid": self.is_valid_bpmn,
            "is_deployed": self.is_deployed_to_camunda,
            "language": self.detected_language,
            "duration_seconds": duration
        }

    def start_session(self) -> None:
        """Mark session start time"""
        self.started_at = datetime.now()

    def end_session(self) -> None:
        """Mark session end time"""
        self.completed_at = datetime.now()

    def reset(self) -> None:
        """Reset session memory to initial state"""
        self.original_description = ""
        self.detected_language = "en"
        self.fix_attempts = []
        self.current_bpmn_xml = ""
        self.current_iteration = 0
        self.camunda_deployment_attempts = []
        self.validation_history = []
        self.is_valid_bpmn = False
        self.is_deployed_to_camunda = False
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert session memory to dictionary for serialization"""
        return {
            "original_description": self.original_description,
            "detected_language": self.detected_language,
            "current_iteration": self.current_iteration,
            "is_valid_bpmn": self.is_valid_bpmn,
            "is_deployed_to_camunda": self.is_deployed_to_camunda,
            "fix_attempts_count": len(self.fix_attempts),
            "deployment_attempts_count": len(self.camunda_deployment_attempts),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stats": self.get_stats()
        }
