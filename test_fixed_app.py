#!/usr/bin/env python3
"""
Quick test to verify the ProMoAgentAI components work after the fix
"""

import sys
import os

def test_imports():
    """Test if all imports work"""
    print("🧪 Testing imports...")
    try:
        from config import Config
        from session_memory import SessionMemory
        from agents import BPMNAgents, BPMNTasks, validate_bpmn_xml, deploy_to_camunda
        from orchestrator import BPMNOrchestrator
        from bpmn_viewer import BPMNViewer
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality"""
    print("\n🔧 Testing basic functionality...")
    try:
        # Test session memory
        memory = SessionMemory()
        memory.original_description = "Test process"
        
        # Test BPMN validation with valid XML
        valid_bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                   id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="myProcess" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1"/>
    <bpmn:endEvent id="EndEvent_1"/>
  </bpmn:process>
</bpmn:definitions>'''
        
        result = validate_bpmn_xml(valid_bpmn)
        if not result["valid"]:
            print(f"❌ BPMN validation failed: {result['error']}")
            return False
        
        print("✅ Basic functionality working")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_agent_creation():
    """Test if agents can be created without errors"""
    print("\n🤖 Testing agent creation...")
    try:
        from session_memory import SessionMemory
        from agents import BPMNAgents
        
        memory = SessionMemory()
        agents = BPMNAgents(memory)
        
        # Try to create each agent
        generator = agents.create_generator_agent()
        validator = agents.create_validator_agent()
        fixer = agents.create_fixer_agent()
        improver = agents.create_improver_agent()
        camunda = agents.create_camunda_agent()
        
        print("✅ All agents created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False

def main():
    print("🚀 Testing Fixed ProMoAgentAI\n")
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not found in environment")
        print("💡 Set it in .env file or export OPENAI_API_KEY=your_key")
    
    tests = [
        ("Imports", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Agent Creation", test_agent_creation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*50)
    print("📋 TEST RESULTS")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The fix was successful.")
        print("💡 You can now run: streamlit run app.py")
    else:
        print(f"\n⚠️  {len(results) - passed} tests still failing.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)