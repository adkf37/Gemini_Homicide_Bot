#!/usr/bin/env python3
"""
LLM Performance Test Suite for MCP Tools
Tests different models on various query types and complexity levels.
"""

import json
import time
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import yaml

from llama_client import LlamaClient
from intelligent_mcp import intelligent_mcp

class LLMPerformanceTester:
    """Test suite for evaluating LLM performance with MCP tools."""
    
    def __init__(self):
        self.test_results = []
        self.models_to_test = self._load_models_from_config()
        
        # Test cases organized by complexity and type
        self.test_cases = {
            "simple_queries": [
                {
                    "question": "How many homicides in 2023?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year"],
                    "complexity": "simple"
                },
                {
                    "question": "What does IUCR mean?",
                    "expected_tool": "get_iucr_info", 
                    "expected_params": [],
                    "complexity": "simple"
                }
            ],
            "which_x_most_queries": [
                {
                    "question": "Which ward had the most homicides in 2013?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year", "group_by"],
                    "expected_group_by": "ward",
                    "complexity": "medium"
                },
                {
                    "question": "What district had the most homicides from 2020 to 2022?",
                    "expected_tool": "query_homicides_advanced", 
                    "expected_params": ["start_year", "end_year", "group_by"],
                    "expected_group_by": "district",
                    "complexity": "medium"
                }
            ],
            "top_n_queries": [
                {
                    "question": "Show me the top 3 districts with the most homicides from 2020 to 2022",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year", "group_by", "top_n"],
                    "expected_group_by": "district",
                    "expected_top_n": 3,
                    "complexity": "medium"
                }
            ],
            "complex_multi_criteria": [
                {
                    "question": "What are the top 2 wards with the most homicides where no arrests were made?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["arrest_status", "group_by", "top_n"],
                    "expected_group_by": "ward",
                    "expected_top_n": 2,
                    "expected_arrest_status": False,
                    "complexity": "complex"
                },
                {
                    "question": "Show me the top 5 community areas with domestic homicides",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["domestic", "group_by", "top_n"],
                    "expected_group_by": "community_area",
                    "expected_top_n": 5,
                    "expected_domestic": True,
                    "complexity": "complex"
                },
                {
                    "question": "From 2015 to 2019, which district had the most non-domestic homicides with no arrests? Show top 3.",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year", "group_by", "top_n", "domestic", "arrest_status"],
                    "expected_group_by": "district",
                    "expected_top_n": 3,
                    "expected_domestic": False,
                    "expected_arrest_status": False,
                    "complexity": "complex"
                },
                {
                    "question": "What are the top 4 wards with domestic homicides in 2022 where arrests were made?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year", "group_by", "top_n", "domestic", "arrest_status"],
                    "expected_group_by": "ward",
                    "expected_top_n": 4,
                    "expected_domestic": True,
                    "expected_arrest_status": True,
                    "complexity": "complex"
                }
            ],
            "negative_cases": [
                {
                    "question": "What is the weather like in Chicago?",
                    "expected_tool": None,
                    "expected_params": [],
                    "complexity": "simple",
                    "should_not_use_tools": True
                },
                {
                    "question": "Tell me about Chicago's history",
                    "expected_tool": None,
                    "expected_params": [],
                    "complexity": "simple",
                    "should_not_use_tools": True
                },
                {
                    "question": "What is IUCR?",
                    "expected_tool": "get_iucr_info",
                    "expected_params": [],
                    "complexity": "simple",
                    "should_not_use_tools": False
                }
            ],
            "year_range_variations": [
                {
                    "question": "How many homicides from 2018 through 2020?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year"],
                    "expected_start_year": 2018,
                    "expected_end_year": 2020,
                    "complexity": "medium"
                },
                {
                    "question": "Which ward had the most homicides between 2019 and 2023?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["start_year", "end_year", "group_by"],
                    "expected_group_by": "ward",
                    "expected_start_year": 2019,
                    "expected_end_year": 2023,
                    "complexity": "medium"
                }
            ],
            "synonym_variations": [
                {
                    "question": "What community area has the highest number of killings?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["group_by"],
                    "expected_group_by": "community_area",
                    "complexity": "medium"
                },
                {
                    "question": "Which police district has the least murders?",
                    "expected_tool": "query_homicides_advanced",
                    "expected_params": ["group_by"],
                    "expected_group_by": "district",
                    "complexity": "medium"
                }
            ]
        }
    
    def _load_models_from_config(self) -> List[str]:
        """Load model names from model_configs.yaml for consistent evaluation."""
        config_path = Path("model_configs.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                models_section = config_data.get("models", {})
                if isinstance(models_section, dict) and models_section:
                    return list(models_section.keys())
            except Exception as e:
                print(f"⚠️  Could not load models from configuration: {e}")

        # Fallback to Gemini defaults
        return [
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest"
        ]

    def test_model(self, model_name: str) -> Dict[str, Any]:
        """Test a specific model against all test cases."""
        print(f"\n🧪 Testing model: {model_name}")
        print("=" * 50)
        
        try:
            client = LlamaClient(model_name=model_name)
            model_results = {
                "model": model_name,
                "timestamp": datetime.now().isoformat(),
                "categories": {},
                "overall_score": 0,
                "total_tests": 0,
                "passed_tests": 0,
                "errors": []
            }
            
            for category, test_cases in self.test_cases.items():
                print(f"\n📋 Testing {category}...")
                category_results = []
                
                for i, test_case in enumerate(test_cases, 1):
                    print(f"  {i}. {test_case['question'][:50]}...")
                    result = self.run_single_test(client, test_case)
                    category_results.append(result)
                    
                    model_results["total_tests"] += 1
                    if result["passed"]:
                        model_results["passed_tests"] += 1
                    
                    if result.get("error"):
                        model_results["errors"].append({
                            "question": test_case["question"],
                            "error": result["error"]
                        })
                
                model_results["categories"][category] = category_results
            
            # Calculate overall score
            if model_results["total_tests"] > 0:
                model_results["overall_score"] = (
                    model_results["passed_tests"] / model_results["total_tests"]
                ) * 100
            
            return model_results
            
        except Exception as e:
            return {
                "model": model_name,
                "error": f"Failed to initialize model: {str(e)}",
                "overall_score": 0
            }
    
    def run_single_test(self, client: LlamaClient, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case and evaluate the result."""
        start_time = time.time()
        result = {
            "question": test_case["question"],
            "complexity": test_case["complexity"],
            "passed": False,
            "response_time": 0,
            "tool_called": None,
            "parameters_used": {},
            "issues": []
        }

        try:
            # Generate response using the intelligent MCP handler
            interaction = intelligent_mcp.handle_question_with_tools(
                test_case["question"],
                client,
                include_trace=True
            )

            result["response_time"] = time.time() - start_time

            if not isinstance(interaction, dict):
                # Unexpected fallback scenario
                response_text = str(interaction)
                result["response"] = response_text[:200] + "..." if len(response_text) > 200 else response_text
                result["issues"].append("Trace information unavailable")
                return result

            final_answer = interaction.get("final_answer", "") or ""
            result["response"] = final_answer[:200] + "..." if len(final_answer) > 200 else final_answer
            result["trace"] = interaction

            expected_tool = test_case.get("expected_tool")
            tool_call = interaction.get("tool_call") or {}
            tool_execution = interaction.get("tool_execution") or {}

            result["tool_called"] = tool_call.get("name") if isinstance(tool_call, dict) else None
            result["parameters_used"] = tool_call.get("arguments", {}) if isinstance(tool_call, dict) else {}
            result["tool_latency"] = tool_execution.get("latency_seconds")

            if expected_tool and result["tool_called"] != expected_tool:
                result["issues"].append(
                    f"Expected tool '{expected_tool}' but model called '{result['tool_called']}'"
                )

            if expected_tool and not interaction.get("needs_tool_call", False):
                result["issues"].append("Model did not request tool usage")

            # Validate required parameters
            expected_params = test_case.get("expected_params", [])
            for param in expected_params:
                if param not in result["parameters_used"]:
                    result["issues"].append(f"Missing expected parameter '{param}'")

            # Specific value checks
            expected_group_by = test_case.get("expected_group_by")
            if expected_group_by is not None:
                group_value = result["parameters_used"].get("group_by")
                if group_value != expected_group_by:
                    result["issues"].append(
                        f"Expected group_by '{expected_group_by}' but got '{group_value}'"
                    )

            if "expected_top_n" in test_case:
                top_n_value = result["parameters_used"].get("top_n")
                if top_n_value != test_case["expected_top_n"]:
                    result["issues"].append(
                        f"Expected top_n {test_case['expected_top_n']} but got {top_n_value}"
                    )

            if "expected_arrest_status" in test_case:
                arrest_value = result["parameters_used"].get("arrest_status")
                if arrest_value != test_case["expected_arrest_status"]:
                    result["issues"].append(
                        f"Expected arrest_status {test_case['expected_arrest_status']} but got {arrest_value}"
                    )

            if "expected_domestic" in test_case:
                domestic_value = result["parameters_used"].get("domestic")
                if domestic_value != test_case["expected_domestic"]:
                    result["issues"].append(
                        f"Expected domestic {test_case['expected_domestic']} but got {domestic_value}"
                    )

            # Year range validations
            if "expected_start_year" in test_case:
                start_year_value = result["parameters_used"].get("start_year")
                if start_year_value != test_case["expected_start_year"]:
                    result["issues"].append(
                        f"Expected start_year {test_case['expected_start_year']} but got {start_year_value}"
                    )

            if "expected_end_year" in test_case:
                end_year_value = result["parameters_used"].get("end_year")
                if end_year_value != test_case["expected_end_year"]:
                    result["issues"].append(
                        f"Expected end_year {test_case['expected_end_year']} but got {end_year_value}"
                    )

            # Negative case validation: should NOT use tools
            if test_case.get("should_not_use_tools") and interaction.get("needs_tool_call"):
                result["issues"].append(
                    "Model incorrectly requested tool usage for non-homicide question"
                )

            if expected_tool and tool_execution.get("error"):
                result["issues"].append(f"Tool execution error: {tool_execution.get('error')}")

            # Answer consistency validation
            if not tool_execution.get("error") and result["tool_called"]:
                consistency_issues = self._validate_answer_consistency(
                    final_answer,
                    tool_execution.get("raw_result"),
                    test_case
                )
                result["issues"].extend(consistency_issues)

            result["passed"] = len(result["issues"]) == 0

        except Exception as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time

        return result
    
    def _validate_answer_consistency(self, answer: str, tool_result: Any, test_case: Dict[str, Any]) -> List[str]:
        """Validate that the answer is consistent with the tool result."""
        issues = []
        
        if not tool_result or not isinstance(tool_result, dict):
            return issues
        
        answer_lower = answer.lower()
        
        # For group_by queries, check if top result is mentioned in answer
        if test_case.get("expected_group_by"):
            primary_breakdown = tool_result.get("primary_breakdown", {})
            if primary_breakdown and "data" in primary_breakdown:
                breakdown_data = primary_breakdown["data"]
                if breakdown_data:
                    # Get the top item
                    sorted_items = sorted(breakdown_data.items(), key=lambda x: x[1], reverse=True)
                    if sorted_items:
                        top_item, top_count = sorted_items[0]
                        top_item_str = str(top_item).lower()
                        
                        # Check if top item is mentioned in answer
                        if top_item_str not in answer_lower and top_item not in answer_lower:
                            issues.append(
                                f"Answer does not mention the top {test_case['expected_group_by']} '{top_item}' "
                                f"which had {top_count} cases"
                            )
        
        # For count queries, verify numeric consistency
        if "total_matches" in tool_result:
            total_matches = tool_result["total_matches"]
            # Look for numbers in answer that are way off
            import re
            numbers_in_answer = re.findall(r'\b\d+\b', answer)
            if numbers_in_answer:
                # Check if the correct total is mentioned somewhere
                if str(total_matches) not in numbers_in_answer:
                    # Allow for some flexibility (within 10% or mentioning related stats)
                    has_close_number = any(
                        abs(int(num) - total_matches) / max(total_matches, 1) < 0.1
                        for num in numbers_in_answer if num.isdigit()
                    )
                    if not has_close_number and total_matches > 10:
                        issues.append(
                            f"Answer mentions numbers {numbers_in_answer} but tool found {total_matches} total matches"
                        )
        
        return issues
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run tests on all available models."""
        print("🚀 Starting LLM Performance Test Suite")
        print("=" * 60)
        
        all_results = {
            "test_suite_version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "models_tested": [],
            "summary": {}
        }
        
        # Check which models are actually available
        available_models = self.check_available_models()
        
        for model in available_models:
            try:
                model_results = self.test_model(model)
                all_results["models_tested"].append(model_results)
                
                print(f"\n✅ {model}: {model_results.get('overall_score', 0):.1f}% pass rate")
                
            except Exception as e:
                print(f"\n❌ {model}: Failed to test - {e}")
                all_results["models_tested"].append({
                    "model": model,
                    "error": str(e),
                    "overall_score": 0
                })
        
        # Generate summary
        all_results["summary"] = self.generate_summary(all_results["models_tested"])
        
        return all_results
    
    def check_available_models(self) -> List[str]:
        """Return configured models for testing."""
        print("🔍 Using configured Gemini models for testing...")
        if self.models_to_test:
            for model in self.models_to_test:
                print(f"  ✅ {model}")
            return self.models_to_test

        fallback = ["gemini-1.5-pro-latest"]
        print("  ⚠️  No models configured; falling back to gemini-1.5-pro-latest")
        return fallback
    
    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of all test results."""
        summary = {
            "best_model": None,
            "worst_model": None,
            "average_score": 0,
            "models_by_score": []
        }
        
        valid_results = [r for r in results if "overall_score" in r and not r.get("error")]
        
        if valid_results:
            # Sort by score
            sorted_results = sorted(valid_results, key=lambda x: x["overall_score"], reverse=True)
            
            summary["best_model"] = sorted_results[0]["model"]
            summary["worst_model"] = sorted_results[-1]["model"]
            summary["average_score"] = sum(r["overall_score"] for r in valid_results) / len(valid_results)
            summary["models_by_score"] = [(r["model"], r["overall_score"]) for r in sorted_results]
        
        return summary
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None):
        """Save test results to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"llm_test_results_{timestamp}.json"
        
        filepath = Path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filepath.absolute()}")
    
    def print_detailed_report(self, results: Dict[str, Any]):
        """Print a detailed report of the test results."""
        print("\n" + "="*60)
        print("📊 DETAILED TEST RESULTS REPORT")
        print("="*60)
        
        summary = results["summary"]
        
        print(f"\n🏆 SUMMARY:")
        print(f"  Best Model: {summary.get('best_model', 'N/A')}")
        print(f"  Average Score: {summary.get('average_score', 0):.1f}%")
        
        print(f"\n📈 MODELS BY PERFORMANCE:")
        for model, score in summary.get("models_by_score", []):
            print(f"  {model}: {score:.1f}%")
        
        print(f"\n📋 DETAILED BREAKDOWN:")
        for model_result in results["models_tested"]:
            if model_result.get("error"):
                print(f"\n❌ {model_result['model']}: ERROR - {model_result['error']}")
                continue
            
            model = model_result["model"]
            score = model_result.get("overall_score", 0)
            passed = model_result.get("passed_tests", 0)
            total = model_result.get("total_tests", 0)
            
            print(f"\n📊 {model} ({score:.1f}% - {passed}/{total})")
            
            for category, cat_results in model_result.get("categories", {}).items():
                category_passed = sum(1 for r in cat_results if r.get("passed", False))
                category_total = len(cat_results)
                print(f"  {category}: {category_passed}/{category_total}")
                
                for test in cat_results:
                    status = "✅" if test.get("passed", False) else "❌"
                    time_ms = test.get("response_time", 0) * 1000
                    print(f"    {status} {test['question'][:40]}... ({time_ms:.0f}ms)")
                    
                    if test.get("issues"):
                        for issue in test["issues"]:
                            print(f"        ⚠️  {issue}")

def main():
    """Main function to run the test suite."""
    tester = LLMPerformanceTester()
    
    print("This will test different LLMs with the MCP homicide data tools.")
    print("Ensure GOOGLE_API_KEY is set and the configured Gemini models are accessible.")
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Save results
    tester.save_results(results)
    
    # Print detailed report
    tester.print_detailed_report(results)
    
    print(f"\n🎉 Testing complete! Check the JSON file for detailed results.")

if __name__ == "__main__":
    main()
