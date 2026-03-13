"""
Enhanced BPMN Orchestrator
Coordinates 13 agents for complete BPMN generation workflow
"""

from crewai import Crew, Agent, Task
from agents import (
    BPMNAgents, BPMNTasks, deploy_to_camunda,
    validate_bpmn_xml, create_llm, add_camunda_namespace,
    ensure_process_executable, add_history_time_to_live
)
from session_memory import SessionMemory
from validation import validate_bpmn_comprehensive, detect_language
import streamlit as st
import re
import os
from config import Config

Config.validate()

# Set environment variables based on selected model
model_config = Config.get_current_model_config()
if model_config["provider"] == "openai":
    os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY
elif model_config["provider"] == "anthropic":
    os.environ["ANTHROPIC_API_KEY"] = Config.ANTHROPIC_API_KEY
elif model_config["provider"] == "google":
    os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY


class BPMNOrchestrator:
    """
    Enhanced orchestrator that coordinates 13 specialized agents:
    1. Master Orchestrator - Coordinates workflow
    2. Generator - Creates initial BPMN
    3. Validator - Validates syntax
    4. Fixer - Fixes errors
    5. Visualizer - Adds diagram elements
    6. Camunda Optimizer - Camunda compatibility
    7. Deployment - Deploys to Camunda
    8. Improver - Fixes deployment errors
    9. Reviewer - Requirements check
    10. Process Analyzer - Bottleneck analysis
    11. Lane Designer (NEW) - Designs swim lanes
    12. Edge Validator (NEW) - Validates edges/flows
    13. Diagram Layouter (NEW) - Calculates coordinates
    """

    def __init__(self):
        self.session_memory = SessionMemory()
        self.agents = BPMNAgents(self.session_memory)
        self.tasks = BPMNTasks(self.session_memory)
        self.max_fix_iterations = 5
        self.max_camunda_attempts = 3
        self.llm = create_llm(temperature=0.1)
        self.master_orchestrator = self.create_master_orchestrator()

    def create_master_orchestrator(self):
        """Create the master orchestrator agent"""
        return Agent(
            role="Master BPMN Orchestrator",
            goal="Produce complete, valid BPMN matching requirements with proper visualization",
            backstory="""Master orchestrator managing the complete BPMN workflow.
            Coordinates all 13 specialized agents to ensure:
            - Complete edge connections
            - Semantic accuracy
            - Proper swim lanes
            - Camunda compatibility
            - Valid diagram layout

            Workflow phases:
            1. Lane Design - Identify actors and create lanes
            2. Generation - Create BPMN structure
            3. Layout - Calculate coordinates
            4. Edge Validation - Ensure all edges exist
            5. Validation - Check structure
            6. Camunda Optimization - Prepare for deployment

            Output raw XML only, no markdown.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )

    def reset_session(self):
        """Reset the session memory for a new process"""
        self.session_memory.reset()
        self.agents = BPMNAgents(self.session_memory)
        self.tasks = BPMNTasks(self.session_memory)
        self.master_orchestrator = self.create_master_orchestrator()

    def clean_xml_output(self, xml_string: str) -> str:
        """Remove markdown formatting from XML output"""
        if "```xml" in xml_string:
            match = re.search(r'```xml\s*(.*?)\s*```', xml_string, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in xml_string:
            match = re.search(r'```\s*(.*?)\s*```', xml_string, re.DOTALL)
            if match:
                return match.group(1).strip()

        # Also try to extract just the XML part
        if '<?xml' in xml_string:
            start = xml_string.find('<?xml')
            # Find the closing definitions tag
            end = xml_string.rfind('</bpmn:definitions>')
            if end == -1:
                end = xml_string.rfind('</definitions>')
            if end != -1:
                return xml_string[start:end + len('</bpmn:definitions>')].strip()
            return xml_string[start:].strip()

        if '<bpmn:definitions' in xml_string:
            start = xml_string.find('<bpmn:definitions')
            end = xml_string.rfind('</bpmn:definitions>')
            if end != -1:
                return xml_string[start:end + len('</bpmn:definitions>')].strip()
            return xml_string[start:].strip()

        return xml_string.strip()

    def simple_bpmn_generation(self, description: str) -> tuple:
        """Simplified BPMN generation as fallback"""
        log = []
        try:
            generator = self.agents.create_generator_agent()
            gen_task = self.tasks.create_generation_task(description, generator)

            gen_crew = Crew(agents=[generator], tasks=[gen_task], verbose=False, max_execution_time=120)
            result = gen_crew.kickoff()
            bpmn_xml = self.clean_xml_output(str(result))
            log.append("Phase 1: Simple generation completed")

            return True, bpmn_xml, "Simple generation successful", log
        except Exception as e:
            log.append(f"Simple generation failed: {str(e)}")
            return False, "", f"Simple generation failed: {str(e)}", log

    def orchestrate_bpmn_generation(self, description: str) -> tuple:
        """
        Enhanced BPMN generation with all 13 agents

        Workflow:
        1. Generator creates initial BPMN
        2. Edge Validator ensures all edges exist
        3. Diagram Layouter calculates coordinates
        4. Reviewer checks requirements
        5. Fixer repairs any issues
        6. Visualizer adds diagram elements
        7. Syntax Validator checks structure
        8. Camunda Optimizer prepares for deployment
        """
        log = []
        self.session_memory.original_description = description

        try:
            # Phase 1: Generate initial BPMN
            log.append("Phase 1: Generating initial BPMN...")
            generator = self.agents.create_generator_agent()
            gen_task = self.tasks.create_generation_task(description, generator)

            gen_crew = Crew(agents=[generator], tasks=[gen_task], verbose=False, max_execution_time=180)
            result = gen_crew.kickoff()
            bpmn_xml = self.clean_xml_output(str(result))
            log.append("Phase 1: Generated initial BPMN")

            # Phase 2: Validate edges and add missing ones
            log.append("Phase 2: Validating edges...")
            edge_validator = self.agents.create_edge_validator_agent()
            edge_task = self.tasks.create_edge_validation_task(bpmn_xml, edge_validator)

            edge_crew = Crew(agents=[edge_validator], tasks=[edge_task], verbose=False, max_execution_time=120)
            edge_result = edge_crew.kickoff()
            bpmn_xml = self.clean_xml_output(str(edge_result))
            log.append("Phase 2: Edges validated and fixed")

            # Phase 3: Review against requirements
            log.append("Phase 3: Reviewing against requirements...")
            reviewer = self.agents.create_reviewer_agent()
            review_task = self.tasks.create_review_task(bpmn_xml, reviewer)

            review_crew = Crew(agents=[reviewer], tasks=[review_task], verbose=False)
            review_result = str(review_crew.kickoff())

            if "VERDICT: NO_PASS" in review_result:
                # Fix based on review
                fixer = self.agents.create_fixer_agent()
                feedback = review_result.split("FEEDBACK:")[1] if "FEEDBACK:" in review_result else "Issues found"
                fix_task = self.tasks.create_fixing_task(bpmn_xml, feedback, fixer)

                fix_crew = Crew(agents=[fixer], tasks=[fix_task], verbose=False)
                fix_result = str(fix_crew.kickoff())

                if "FIXED_XML:" in fix_result:
                    bpmn_xml = self.clean_xml_output(fix_result.split("FIXED_XML:")[1].split("FIX_DESCRIPTION:")[0])
                    log.append("Phase 3: Fixed based on review feedback")
            else:
                log.append("Phase 3: Review passed")

            # Phase 4: Layout calculation
            log.append("Phase 4: Calculating diagram layout...")
            layouter = self.agents.create_diagram_layouter_agent()
            layout_task = self.tasks.create_layout_task(bpmn_xml, layouter)

            layout_crew = Crew(agents=[layouter], tasks=[layout_task], verbose=False)
            layout_result = layout_crew.kickoff()
            bpmn_xml = self.clean_xml_output(str(layout_result))
            log.append("Phase 4: Layout calculated")

            # Phase 5: Prepare for visualization
            log.append("Phase 5: Adding visualization elements...")
            visualizer = self.agents.create_visualizer_agent()
            viz_task = self.tasks.create_visualization_task(bpmn_xml, visualizer)

            viz_crew = Crew(agents=[visualizer], tasks=[viz_task], verbose=False)
            viz_result = viz_crew.kickoff()
            bpmn_xml = self.clean_xml_output(str(viz_result))
            log.append("Phase 5: Added diagram elements for visualization")

            # Phase 6: Validate syntax
            log.append("Phase 6: Validating syntax...")
            val_result = validate_bpmn_xml(bpmn_xml)

            if not val_result["valid"]:
                fixer = self.agents.create_fixer_agent()
                fix_task = self.tasks.create_fixing_task(bpmn_xml, val_result["error"], fixer)

                fix_crew = Crew(agents=[fixer], tasks=[fix_task], verbose=False)
                fix_result = str(fix_crew.kickoff())

                if "FIXED_XML:" in fix_result:
                    bpmn_xml = self.clean_xml_output(fix_result.split("FIXED_XML:")[1].split("FIX_DESCRIPTION:")[0])
                    log.append("Phase 6: Fixed syntax issues")
            else:
                log.append("Phase 6: Syntax valid")

            # Phase 7: Optimize for Camunda deployment
            log.append("Phase 7: Optimizing for Camunda...")
            optimizer = self.agents.create_camunda_optimizer_agent()
            opt_task = self.tasks.create_camunda_optimization_task(bpmn_xml, optimizer)

            opt_crew = Crew(agents=[optimizer], tasks=[opt_task], verbose=False)
            opt_result = opt_crew.kickoff()
            bpmn_xml = self.clean_xml_output(str(opt_result))
            log.append("Phase 7: Optimized for Camunda deployment")

            self.session_memory.current_bpmn_xml = bpmn_xml
            return True, bpmn_xml, "Generation successful", log

        except Exception as e:
            log.append(f"Error: {str(e)}")
            return False, "", f"Failed: {str(e)}", log

    def generate_and_review_bpmn(self, description: str) -> tuple:
        """Generate initial BPMN from process description and review it"""
        review_log = []
        max_generation_attempts = 3

        for attempt in range(max_generation_attempts):
            try:
                self.session_memory.original_description = description

                # Create generator agent and task
                generator_agent = self.agents.create_generator_agent()
                generation_task = self.tasks.create_generation_task(description, generator_agent)

                # Create crew and execute
                crew = Crew(
                    agents=[generator_agent],
                    tasks=[generation_task],
                    verbose=True
                )

                result = crew.kickoff()
                bpmn_xml = self.clean_xml_output(str(result))

                # Review the generated BPMN
                reviewer_agent = self.agents.create_reviewer_agent()
                review_task = self.tasks.create_review_task(bpmn_xml, reviewer_agent)

                review_crew = Crew(
                    agents=[reviewer_agent],
                    tasks=[review_task],
                    verbose=True
                )

                review_result = str(review_crew.kickoff())

                # Parse review result
                if "VERDICT: PASS" in review_result:
                    review_log.append(f"Generation attempt {attempt + 1}: Review PASSED")
                    self.session_memory.current_bpmn_xml = bpmn_xml
                    return True, bpmn_xml, "BPMN generated and reviewed successfully", review_log
                else:
                    # Extract feedback
                    feedback = ""
                    if "FEEDBACK:" in review_result:
                        feedback = review_result.split("FEEDBACK:")[1].strip()
                    review_log.append(f"Generation attempt {attempt + 1}: Review FAILED - {feedback}")

                    # Update the description with feedback for next attempt
                    if attempt < max_generation_attempts - 1:
                        description = f"{self.session_memory.original_description}\n\nIMPORTANT: Previous attempt failed review with feedback: {feedback}\nPlease ensure ALL mentioned steps and logic are included."
                        review_log.append("Regenerating with review feedback...")

            except Exception as e:
                review_log.append(f"Generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_generation_attempts - 1:
                    return False, "", f"Generation failed after {max_generation_attempts} attempts", review_log

        # If we exhausted all attempts
        return False, bpmn_xml, f"Failed review after {max_generation_attempts} attempts", review_log

    def validate_and_fix_loop(self, bpmn_xml: str) -> tuple:
        """Execute the validation and fixing loop"""
        fix_log = []
        current_xml = bpmn_xml

        for iteration in range(self.max_fix_iterations):
            # Validate current XML using comprehensive validator
            validation_result = validate_bpmn_comprehensive(current_xml)

            if validation_result["valid"]:
                self.session_memory.is_valid_bpmn = True
                self.session_memory.current_bpmn_xml = current_xml
                fix_log.append(f"Iteration {iteration + 1}: Validation successful")
                return True, current_xml, fix_log

            # Record the validation failures
            errors = validation_result.get("errors", [])
            error_message = "; ".join(errors[:3])  # First 3 errors
            fix_log.append(f"Iteration {iteration + 1}: {error_message}")

            # Use fixer agent to repair the XML
            try:
                fixer_agent = self.agents.create_fixer_agent()
                fixing_task = self.tasks.create_fixing_task(current_xml, error_message, fixer_agent)

                crew = Crew(
                    agents=[fixer_agent],
                    tasks=[fixing_task],
                    verbose=True
                )

                result = crew.kickoff()
                result_str = str(result)

                # Parse the fix result
                if "FIXED_XML:" in result_str and "FIX_DESCRIPTION:" in result_str:
                    xml_match = re.search(r'FIXED_XML:\s*(.*?)\s*FIX_DESCRIPTION:', result_str, re.DOTALL)
                    desc_match = re.search(r'FIX_DESCRIPTION:\s*(.*?)$', result_str, re.DOTALL)

                    if xml_match and desc_match:
                        fixed_xml = xml_match.group(1).strip()
                        fix_description = desc_match.group(1).strip()

                        # Clean up XML
                        fixed_xml = self.clean_xml_output(fixed_xml)

                        # Record the fix attempt
                        self.session_memory.add_fix_attempt(
                            error_message=error_message,
                            fix_description=fix_description,
                            bpmn_xml=fixed_xml,
                            success=False
                        )

                        current_xml = fixed_xml
                        fix_log.append(f"Fix applied: {fix_description}")
                    else:
                        fix_log.append("Failed to parse fix result from agent")
                        break
                else:
                    # Fallback: treat entire result as fixed XML
                    current_xml = self.clean_xml_output(result_str)
                    self.session_memory.add_fix_attempt(
                        error_message=error_message,
                        fix_description="Agent attempted general fix",
                        bpmn_xml=current_xml,
                        success=False
                    )
                    fix_log.append("Fix applied (fallback parsing)")

            except Exception as e:
                fix_log.append(f"Fix attempt failed: {str(e)}")
                break

        # If we get here, we've exceeded max iterations
        fix_log.append(f"Maximum fix iterations ({self.max_fix_iterations}) reached")
        return False, current_xml, fix_log

    def deploy_to_camunda_with_retry(self, bpmn_xml: str) -> tuple:
        """Enhanced Camunda deployment with optimization"""
        log = []
        current_xml = bpmn_xml

        try:
            optimizer = self.agents.create_camunda_optimizer_agent()
            deployer = self.agents.create_deployment_agent()

            for attempt in range(self.max_camunda_attempts):
                # Optimize
                opt_task = self.tasks.create_camunda_optimization_task(current_xml, optimizer)
                opt_crew = Crew(agents=[optimizer], tasks=[opt_task], verbose=False)
                opt_result = opt_crew.kickoff()
                current_xml = self.clean_xml_output(str(opt_result))

                # Apply additional Camunda fixes
                current_xml = add_camunda_namespace(current_xml)
                current_xml = ensure_process_executable(current_xml)
                current_xml = add_history_time_to_live(current_xml)

                # Deploy
                deployment_result = deploy_to_camunda(current_xml)

                # Record deployment attempt in session memory
                self.session_memory.add_camunda_attempt(
                    response_data=deployment_result,
                    success=deployment_result["success"]
                )

                if deployment_result["success"]:
                    log.append(f"Deployed on attempt {attempt + 1}")
                    return True, deployment_result, log

                # Fix based on error
                error = deployment_result.get("error", "Unknown error")
                log.append(f"Attempt {attempt + 1}: {error}")

                if attempt < self.max_camunda_attempts - 1:
                    improver = self.agents.create_improver_agent()
                    fix_task = self.tasks.create_improvement_task(current_xml, error, improver)

                    fix_crew = Crew(agents=[improver], tasks=[fix_task], verbose=False)
                    fix_result = fix_crew.kickoff()
                    current_xml = self.clean_xml_output(str(fix_result))
                    log.append("Fixed for Camunda")

        except Exception as e:
            log.append(f"Deployment failed: {str(e)}")

        return False, {"error": "Max attempts reached"}, log

    def execute_full_workflow(self, description: str) -> dict:
        """Execute the complete workflow with master orchestration"""
        workflow_result = {
            "success": False,
            "bpmn_xml": "",
            "orchestration_log": [],
            "review_log": [],
            "fix_log": [],
            "deployment_log": [],
            "final_status": "",
            "session_memory": self.session_memory,
            "validation_result": None,
            "language": detect_language(description)
        }

        # Step 1: Try Master Orchestrator first
        try:
            gen_success, bpmn_xml, gen_message, orchestration_log = self.orchestrate_bpmn_generation(description)
            workflow_result["orchestration_log"] = orchestration_log
        except Exception as e:
            orchestration_log = [f"Orchestration failed: {str(e)}"]
            workflow_result["orchestration_log"] = orchestration_log
            gen_success = False

        if not gen_success:
            # Fallback 1: Simple generation
            gen_success, bpmn_xml, gen_message, simple_log = self.simple_bpmn_generation(description)
            workflow_result["orchestration_log"].extend(simple_log)

        if not gen_success:
            # Fallback 2: Traditional generation with review
            gen_success, bpmn_xml, gen_message, review_log = self.generate_and_review_bpmn(description)
            workflow_result["review_log"] = review_log

        if not gen_success:
            workflow_result["final_status"] = f"Generation/Review failed: {gen_message}"
            return workflow_result

        workflow_result["bpmn_xml"] = bpmn_xml

        # Step 2: Validate and fix loop
        val_success, final_xml, fix_log = self.validate_and_fix_loop(bpmn_xml)
        workflow_result["fix_log"] = fix_log
        workflow_result["bpmn_xml"] = final_xml

        # Store comprehensive validation result
        workflow_result["validation_result"] = validate_bpmn_comprehensive(final_xml)

        if not val_success:
            # Even if validation isn't perfect, we might still have usable XML
            if final_xml and '<?xml' in final_xml or '<bpmn:definitions' in final_xml:
                workflow_result["success"] = True
                workflow_result["final_status"] = "Generated with warnings (some validation issues remain)"
            else:
                workflow_result["final_status"] = "Validation/fixing failed after maximum attempts"
            return workflow_result

        # Step 3: Deploy to Camunda (optional - only if Camunda is available)
        try:
            deploy_success, deploy_result, deployment_log = self.deploy_to_camunda_with_retry(final_xml)
            workflow_result["deployment_log"] = deployment_log

            if deploy_success:
                workflow_result["success"] = True
                workflow_result["final_status"] = "Successfully deployed to Camunda"
            else:
                # Still successful if BPMN is valid, just deployment failed
                workflow_result["success"] = True
                workflow_result["final_status"] = "BPMN generated successfully (Camunda deployment failed)"
        except Exception as e:
            # Camunda not available - that's OK
            workflow_result["success"] = True
            workflow_result["final_status"] = "BPMN generated successfully (Camunda not available)"
            workflow_result["deployment_log"] = [f"Camunda deployment skipped: {str(e)}"]

        return workflow_result

    def generate_with_lanes(self, description: str) -> tuple:
        """
        Generate BPMN with explicit lane design phase

        Uses Lane Designer agent before generation
        """
        log = []
        self.session_memory.original_description = description

        try:
            # Phase 1: Design lanes
            log.append("Phase 1: Designing swim lanes...")
            lane_designer = self.agents.create_lane_designer_agent()
            lane_task = self.tasks.create_lane_design_task(description, lane_designer)

            lane_crew = Crew(agents=[lane_designer], tasks=[lane_task], verbose=False)
            lane_result = lane_crew.kickoff()
            lane_design = str(lane_result)
            log.append("Phase 1: Lanes designed")

            # Phase 2: Generate with lane info
            enhanced_description = f"{description}\n\nLANE DESIGN:\n{lane_design}"
            return self.orchestrate_bpmn_generation(enhanced_description)

        except Exception as e:
            log.append(f"Lane design failed: {str(e)}")
            # Fall back to standard generation
            return self.orchestrate_bpmn_generation(description)
