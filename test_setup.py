#!/usr/bin/env python3
"""
Test script to verify PM Agent system setup
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config import settings
        print("✅ Config module imported successfully")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        from src.schemas import CreateIssueParams, SlackMessageParams
        print("✅ Schemas module imported successfully")
    except Exception as e:
        print(f"❌ Schemas import failed: {e}")
        return False
    
    try:
        from src.tools.github_tools import create_issue
        from src.tools.slack_tools import send_message
        print("✅ Tools modules imported successfully")
    except Exception as e:
        print(f"❌ Tools import failed: {e}")
        return False
    
    try:
        from src.agents.planner_agent import create_planner_agent
        from src.agents.reporter_agent import create_reporter_agent
        from src.agents.monitor_agent import create_monitor_agent
        print("✅ Agent modules imported successfully")
    except Exception as e:
        print(f"❌ Agent import failed: {e}")
        return False
    
    try:
        from src.crew import PMAgentCrew
        print("✅ Crew module imported successfully")
    except Exception as e:
        print(f"❌ Crew import failed: {e}")
        return False
    
    return True

def test_agent_creation():
    """Test that agents can be created."""
    print("\nTesting agent creation...")
    
    try:
        from src.agents.planner_agent import create_planner_agent
        from src.agents.reporter_agent import create_reporter_agent
        from src.agents.monitor_agent import create_monitor_agent
        
        planner = create_planner_agent()
        reporter = create_reporter_agent()
        monitor = create_monitor_agent()
        
        print("✅ All agents created successfully")
        print(f"  - Planner: {planner.role}")
        print(f"  - Reporter: {reporter.role}")
        print(f"  - Monitor: {monitor.role}")
        return True
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False

def test_crew_creation():
    """Test that the crew can be created."""
    print("\nTesting crew creation...")
    
    try:
        from src.crew import PMAgentCrew
        
        crew = PMAgentCrew()
        print("✅ PM Agent Crew created successfully")
        print(f"  - Planner agent: {crew.planner.role}")
        print(f"  - Reporter agent: {crew.reporter.role}")
        print(f"  - Monitor agent: {crew.monitor.role}")
        return True
        
    except Exception as e:
        print(f"❌ Crew creation failed: {e}")
        return False

def check_environment():
    """Check environment configuration."""
    print("\nChecking environment...")
    
    env_file = Path(".env")
    example_env = Path("config.example.env")
    
    if env_file.exists():
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found")
        if example_env.exists():
            print("   💡 Copy config.example.env to .env and configure your API keys")
        else:
            print("   ❌ config.example.env also missing")
    
    required_vars = [
        "OPENAI_API_KEY",
        "GITHUB_TOKEN", 
        "GITHUB_OWNER",
        "GITHUB_REPO",
        "SLACK_BOT_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def main():
    """Run all tests."""
    print("🧪 PM Agent System Setup Test\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Agent Creation", test_agent_creation), 
        ("Crew Creation", test_crew_creation),
        ("Environment Check", check_environment)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print(f"\n{'='*50}")
    print("Test Results Summary")
    print('='*50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 All tests passed! PM Agent system is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file with API keys")
        print("2. Run: python main.py config")
        print("3. Run: python main.py test")
        print("4. Try: python main.py plan 'Build a simple todo app'")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("- Missing dependencies: pip install -r requirements.txt")
        print("- Missing .env file: cp config.example.env .env")
        print("- Import errors: Check Python path and module structure")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 