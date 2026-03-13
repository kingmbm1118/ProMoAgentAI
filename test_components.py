#!/usr/bin/env python3
"""
Test script to verify core components of ProMoAgentAI
Run this to check if all components are properly configured
"""

import sys
from config import Config
from session_memory import SessionMemory
from agents import validate_bpmn_xml

def test_config():
    """Test configuration setup"""
    print("🔧 Testing Configuration...")
    try:
        Config.validate()
        print("✅ Configuration valid")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Please set OPENAI_API_KEY in your .env file")
        return False

def test_session_memory():
    """Test session memory functionality"""
    print("\n💾 Testing Session Memory...")
    try:
        memory = SessionMemory()
        memory.original_description = "Test process"
        memory.add_fix_attempt("Test error", "Test fix", "<xml>test</xml>", success=True)
        
        history = memory.get_fix_history_summary()
        assert "Test error" in history
        assert len(memory.fix_attempts) == 1
        
        print("✅ Session memory working correctly")
        return True
    except Exception as e:
        print(f"❌ Session memory error: {e}")
        return False

def test_bpmn_validation():
    """Test BPMN validation functionality"""
    print("\n🔍 Testing BPMN Validation...")
    try:
        # Test valid BPMN
        valid_bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                   xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" 
                   xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" 
                   id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="myProcess" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1"/>
    <bpmn:endEvent id="EndEvent_1"/>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="EndEvent_1"/>
  </bpmn:process>
</bpmn:definitions>'''
        
        result = validate_bpmn_xml(valid_bpmn)
        if result["valid"]:
            print("✅ BPMN validation working correctly")
            return True
        else:
            print(f"❌ Valid BPMN failed validation: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ BPMN validation error: {e}")
        return False

def test_imports():
    """Test all required imports"""
    print("\n📦 Testing Imports...")
    try:
        import streamlit
        import crewai
        import openai
        import requests
        import xml.etree.ElementTree
        print("✅ All required packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def main():
    """Run all tests"""
    print("🚀 ProMoAgentAI - Component Test\n")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Session Memory", test_session_memory),
        ("BPMN Validation", test_bpmn_validation)
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
        print("\n🎉 All tests passed! Your setup is ready.")
        print("💡 Run: streamlit run app.py")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()