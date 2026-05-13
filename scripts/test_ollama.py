#!/usr/bin/env python
"""
Test script for the Ollama-powered STS Advisor.

Tests:
1. Model connectivity
2. Basic queries
3. Run tracking
4. Conversational advice
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import ollama
from loguru import logger
from src.advisor import STSAdvisor


def test_ollama_connection():
    """Test that Ollama is running and the model is available."""
    print("\n" + "=" * 60)
    print("TEST 1: Ollama Connection")
    print("=" * 60)
    
    try:
        result = ollama.list()
        print("✅ Ollama is running")
        
        # Handle both old dict API and new Pydantic API
        if hasattr(result, 'models'):
            # New Pydantic API
            model_names = [m.model for m in result.models]
        else:
            # Old dict API
            model_names = [m['name'] for m in result.get('models', [])]
        
        print(f"   Available models: {model_names}")
        
        # Check for qwen2.5 or gemma2
        if any('qwen2.5' in name for name in model_names):
            print("✅ Qwen 2.5 model found")
            return True
        elif any('gemma2' in name for name in model_names):
            print("✅ Gemma 2 model found")
            return True
        else:
            print("⚠️ No recommended model found. Available models:", model_names)
            return len(model_names) > 0
            
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("   Make sure Ollama is running: `ollama serve`")
        return False


def test_basic_generation():
    """Test basic text generation."""
    print("\n" + "=" * 60)
    print("TEST 2: Basic Generation")
    print("=" * 60)
    
    try:
        response = ollama.chat(
            model="qwen2.5:7b",
            messages=[{
                "role": "user",
                "content": "In one sentence, what is Slay the Spire?"
            }]
        )
        
        answer = response["message"]["content"]
        print(f"✅ Model responded:")
        print(f"   Q: What is Slay the Spire?")
        print(f"   A: {answer[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False


def test_advisor_queries():
    """Test the advisor's database queries."""
    print("\n" + "=" * 60)
    print("TEST 3: Advisor Database Queries")
    print("=" * 60)
    
    try:
        advisor = STSAdvisor()
        
        # Test card query
        card_result = advisor.query_card("Offering")
        print(f"✅ Card query:")
        print(f"   {card_result}")
        
        # Test relic query
        relic_result = advisor.query_relic("Specimen")
        print(f"\n✅ Relic query:")
        print(f"   {relic_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False


def test_run_tracking():
    """Test run creation and tracking."""
    print("\n" + "=" * 60)
    print("TEST 4: Run Tracking")
    print("=" * 60)
    
    try:
        advisor = STSAdvisor()
        
        # Start a run
        result = advisor.start_run("Silent", 10)
        print(f"✅ Run started:")
        print(f"   {result}")
        
        # Add relics and cards
        advisor.add_relic("Specimen", floor=0, source="boss_swap")
        advisor.add_card("Noxious Fumes", floor=3, source="combat_reward")
        advisor.add_card("Catalyst", floor=5, source="combat_reward")
        
        # Update state
        advisor.update_state(floor=6, hp=55, gold=150)
        
        # Get status
        status = advisor.get_run_status()
        print(f"\n✅ Run status after updates:")
        print(f"   {status}")
        
        # Clean up - end the run
        advisor.end_run(victory=False, killed_by="Test")
        
        return True
        
    except Exception as e:
        print(f"❌ Run tracking failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategic_advice():
    """Test getting strategic advice from the LLM."""
    print("\n" + "=" * 60)
    print("TEST 5: Strategic Advice (LLM Chat)")
    print("=" * 60)
    
    try:
        advisor = STSAdvisor()
        
        # Start a run for context
        advisor.start_run("Silent", 10)
        advisor.add_relic("Specimen", floor=0, source="boss_swap")
        
        # Ask for advice
        print("📝 Asking: 'I got Specimen as my first relic. What build should I go for?'")
        print("   (This may take a moment...)")
        
        response = advisor.chat(
            "I got Specimen as my first relic from a boss swap. "
            "What build path should I follow with Silent?"
        )
        
        print(f"\n✅ Advisor response:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        # Clean up
        advisor.end_run(victory=False, killed_by="Test")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategic advice failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_card_pick_advice():
    """Test card pick recommendations."""
    print("\n" + "=" * 60)
    print("TEST 6: Card Pick Advice")
    print("=" * 60)
    
    try:
        advisor = STSAdvisor()
        
        # Set up scenario
        advisor.start_run("Ironclad", 15)
        advisor.update_state(floor=5, hp=60, gold=100, act=1)
        advisor.add_card("Carnage", floor=3, source="combat_reward")
        advisor.add_relic("Vajra", floor=4, source="elite")
        
        print("📝 Scenario: Ironclad A15, Floor 5, 60/80 HP")
        print("   Deck: Starter + Carnage")
        print("   Relics: Burning Blood, Vajra")
        print("   Card reward: Offering, Shrug It Off, or Uppercut")
        print("   (This may take a moment...)")
        
        response = advisor.chat(
            "I'm on floor 5, Act 1. I just beat an elite and got Vajra. "
            "My card reward choices are: Offering, Shrug It Off, or Uppercut. "
            "Which should I take and why?"
        )
        
        print(f"\n✅ Advisor response:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        advisor.end_run(victory=False, killed_by="Test")
        return True
        
    except Exception as e:
        print(f"❌ Card pick advice failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "=" * 60)
    print("STS ADVISOR - TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Connection
    results["Connection"] = test_ollama_connection()
    
    if not results["Connection"]:
        print("\n❌ Cannot continue without Ollama connection.")
        return results
    
    # Test 2: Basic generation
    results["Generation"] = test_basic_generation()
    
    # Test 3: Database queries
    results["Queries"] = test_advisor_queries()
    
    # Test 4: Run tracking
    results["Run Tracking"] = test_run_tracking()
    
    # Test 5: Strategic advice (requires working LLM)
    if results["Generation"]:
        results["Strategic Advice"] = test_strategic_advice()
        results["Card Pick Advice"] = test_card_pick_advice()
    else:
        results["Strategic Advice"] = False
        results["Card Pick Advice"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    return results


if __name__ == "__main__":
    run_all_tests()
