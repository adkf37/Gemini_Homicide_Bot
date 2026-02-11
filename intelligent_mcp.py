import json
import re
import time
from typing import Dict, Any, Optional, Union, List
import mcp_integration

class IntelligentMCPHandler:
    """Handles intelligent MCP tool calling based on natural language questions."""
    
    def __init__(self):
        # Tools are now fetched dynamically from the domain registry.
        # The list below is a cached copy refreshed on each call to get_tools().
        self._cached_tools: List[Dict[str, Any]] = []
    
    def get_tools(self) -> list:
        """Get available tools from all registered domains."""
        mcp_inst = getattr(mcp_integration, "mcp_integration", None)
        if mcp_inst is not None:
            self._cached_tools = mcp_inst.get_all_tool_definitions()
        return self._cached_tools

    @property
    def tools(self) -> list:
        """Backward-compatible property used by execute_tool_call."""
        if not self._cached_tools:
            return self.get_tools()
        return self._cached_tools
    
    def parse_tool_call(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse a tool call from the LLM response."""
        print(f"🔍 Looking for TOOL_CALL in response: {response_content[:100]}...")
        
        if "TOOL_CALL:" not in response_content:
            print("ℹ️  No TOOL_CALL found in response")
            return None
            
        try:
            # Find the TOOL_CALL: part
            tool_call_start = response_content.find("TOOL_CALL:")
            if tool_call_start == -1:
                print("❌ TOOL_CALL: not found")
                return None
                
            # Find the JSON part starting after "TOOL_CALL:"
            json_start = response_content.find("{", tool_call_start)
            if json_start == -1:
                print("❌ No opening brace found after TOOL_CALL:")
                return None
                
            # Find the matching closing brace using more robust approach
            brace_count = 0
            json_end = json_start
            in_quotes = False
            escape_next = False
            
            for i, char in enumerate(response_content[json_start:], json_start):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_quotes = not in_quotes
                    continue
                
                if not in_quotes:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
            
            # Extract and parse the JSON
            tool_call_json = response_content[json_start:json_end].strip()
            print(f"🔍 Extracted JSON: {tool_call_json}")
            
            # Try to fix common JSON issues
            if not tool_call_json.endswith('}'):
                tool_call_json += '}'
            
            tool_call = json.loads(tool_call_json)
            
            if "name" not in tool_call:
                print("❌ Tool call missing 'name' field")
                return None
                
            # Ensure arguments field exists
            if "arguments" not in tool_call:
                tool_call["arguments"] = {}
                
            print(f"✅ Successfully parsed tool call: {tool_call}")
            return tool_call
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"❌ Error parsing tool call: {e}")
            print(f"❌ Raw response content: {response_content}")
            
            # Try a simpler extraction as fallback
            try:
                # Look for simple patterns like {"name": "tool_name"}
                import re
                pattern = r'TOOL_CALL:\s*(\{[^}]*\})'
                match = re.search(pattern, response_content)
                if match:
                    simple_json = match.group(1)
                    print(f"🔧 Trying fallback parsing: {simple_json}")
                    tool_call = json.loads(simple_json)
                    if "arguments" not in tool_call:
                        tool_call["arguments"] = {}
                    return tool_call
            except:
                pass
                
            return None
    
    def execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return structured execution details."""
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        execution_summary = {
            "tool_name": tool_name,
            "arguments": arguments,
            "raw_result": None,
            "formatted_result": None,
            "error": None
        }

        if not tool_name or tool_name not in [tool["name"] for tool in self.tools]:
            execution_summary["error"] = f"Unknown tool: {tool_name}"
            execution_summary["formatted_result"] = f"❌ Unknown tool: {tool_name}"
            return execution_summary

        try:
            mcp_instance = getattr(mcp_integration, "mcp_integration", None)
            if mcp_instance is None:
                mcp_instance = mcp_integration.MCPIntegration()
            result = mcp_instance.call_tool(str(tool_name), arguments)
            execution_summary["raw_result"] = result

            if isinstance(result, dict) and "error" in result:
                execution_summary["error"] = result["error"]
                execution_summary["formatted_result"] = f"❌ {result['error']}"
            else:
                execution_summary["formatted_result"] = mcp_instance.format_tool_result(result, tool_name=tool_name)

        except Exception as e:
            execution_summary["error"] = str(e)
            execution_summary["formatted_result"] = f"❌ Error executing tool {tool_name}: {e}"

        return execution_summary

    # ------------------------------------------------------------------
    # Multi-tool orchestration constants
    # ------------------------------------------------------------------
    MAX_TOOL_ITERATIONS = 4
    TOTAL_TIMEOUT_SECONDS = 90

    def handle_question_with_tools(
        self,
        question: str,
        llama_client,
        include_trace: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """Handle a question that might require one or more tool calls.

        The LLM is called in a loop: at each iteration it can either emit a
        ``TOOL_CALL:`` to fetch more data, or answer directly if it already
        has enough information.  The loop exits when:
        - The LLM responds without a TOOL_CALL (final answer)
        - The maximum iteration count is reached
        - The total wall-clock timeout is exceeded
        - A duplicate tool call (same name+args) is detected
        """
        print("🔍 Generating response with multi-tool calling capability...")

        interaction_trace: Dict[str, Any] = {
            "question": question,
            "iterations": [],
            "final_answer": None,
        }

        # Accumulate prior tool results across iterations
        prior_tool_results: List[Dict[str, str]] = []
        # Track (tool_name, sorted_args_json) to detect duplicates
        seen_calls: set = set()
        loop_start = time.perf_counter()

        for iteration in range(1, self.MAX_TOOL_ITERATIONS + 1):
            elapsed = time.perf_counter() - loop_start
            if elapsed > self.TOTAL_TIMEOUT_SECONDS:
                timeout_msg = f"⏱️ Multi-tool timeout ({self.TOTAL_TIMEOUT_SECONDS}s) reached after {iteration - 1} tool call(s)."
                print(timeout_msg)
                interaction_trace["final_answer"] = self._synthesize_from_accumulated(
                    question, prior_tool_results, llama_client, timeout_msg
                )
                return interaction_trace if include_trace else interaction_trace["final_answer"]

            print(f"\n--- Iteration {iteration}/{self.MAX_TOOL_ITERATIONS} ---")

            # Ask the LLM (with accumulated prior results for iterations > 1)
            response = llama_client.generate_with_tools(
                question,
                self.tools,
                prior_tool_results=prior_tool_results or None,
            )
            content = response.get("content", "")
            needs_tool = response.get("needs_tool_call", False)

            iter_record: Dict[str, Any] = {
                "iteration": iteration,
                "model_response": content[:500],
                "needs_tool_call": needs_tool,
                "tool_call": None,
                "tool_execution": None,
            }

            print(f"🤖 LLM Response (iter {iteration}): {content[:200]}...")
            print(f"🔧 Needs tool call: {needs_tool}")

            if not needs_tool:
                # LLM has answered — we're done
                print(f"✅ LLM answered directly on iteration {iteration}")
                iter_record["final"] = True
                interaction_trace["iterations"].append(iter_record)
                interaction_trace["final_answer"] = content
                return interaction_trace if include_trace else content

            # Parse the tool call
            tool_call = self.parse_tool_call(content)
            if not tool_call:
                error_msg = f"❌ Could not parse tool call from response (iter {iteration}): {content[:200]}"
                print(error_msg)
                iter_record["error"] = error_msg
                interaction_trace["iterations"].append(iter_record)
                # If we have prior results, try to synthesize anyway
                if prior_tool_results:
                    interaction_trace["final_answer"] = self._synthesize_from_accumulated(
                        question, prior_tool_results, llama_client, "Parse error on follow-up call"
                    )
                else:
                    interaction_trace["final_answer"] = error_msg
                return interaction_trace if include_trace else interaction_trace["final_answer"]

            iter_record["tool_call"] = tool_call

            # Dedup check
            call_key = (tool_call["name"], json.dumps(tool_call.get("arguments", {}), sort_keys=True))
            if call_key in seen_calls:
                print(f"⚠️ Duplicate tool call detected: {tool_call['name']} — stopping loop")
                interaction_trace["iterations"].append(iter_record)
                interaction_trace["final_answer"] = self._synthesize_from_accumulated(
                    question, prior_tool_results, llama_client, "Duplicate tool call detected"
                )
                return interaction_trace if include_trace else interaction_trace["final_answer"]
            seen_calls.add(call_key)

            # Execute the tool
            print(f"🔧 Calling tool: {tool_call['name']} with args: {tool_call.get('arguments', {})}")
            tool_start = time.perf_counter()
            tool_execution = self.execute_tool_call(tool_call)
            tool_execution["latency_seconds"] = time.perf_counter() - tool_start
            iter_record["tool_execution"] = tool_execution
            interaction_trace["iterations"].append(iter_record)

            formatted = tool_execution.get("formatted_result", "")
            print(f"📊 Tool result (first 200 chars): {str(formatted)[:200]}...")

            if tool_execution.get("error"):
                # Tool error is non-fatal; accumulate the error and let LLM continue
                prior_tool_results.append({
                    "tool_name": tool_call["name"],
                    "formatted_result": f"Error: {tool_execution['error']}",
                })
                continue

            # Accumulate successful result
            prior_tool_results.append({
                "tool_name": tool_call["name"],
                "formatted_result": formatted,
            })

        # Exhausted max iterations — synthesize from what we have
        print(f"⚠️ Reached max iterations ({self.MAX_TOOL_ITERATIONS})")
        interaction_trace["final_answer"] = self._synthesize_from_accumulated(
            question, prior_tool_results, llama_client, "Max iterations reached"
        )
        return interaction_trace if include_trace else interaction_trace["final_answer"]

    # ------------------------------------------------------------------
    # Synthesis helper
    # ------------------------------------------------------------------

    def _synthesize_from_accumulated(
        self,
        question: str,
        prior_tool_results: List[Dict[str, str]],
        llama_client,
        reason: str,
    ) -> str:
        """Ask the LLM to synthesize a final answer from accumulated tool results."""
        if not prior_tool_results:
            return f"❌ No tool results to synthesize ({reason})"

        data_sections = []
        for pr in prior_tool_results:
            data_sections.append(f"--- {pr['tool_name']} ---\n{pr['formatted_result']}")
        combined_data = "\n\n".join(data_sections)

        follow_up = (
            f"Based on the following data from multiple tools:\n\n"
            f"{combined_data}\n\n"
            f"Please answer the original question: \"{question}\"\n\n"
            f"Provide a clear, informative answer combining all available data. "
            f"If some data is missing or approximate, note that."
        )
        print(f"🔍 Synthesizing final answer from {len(prior_tool_results)} tool result(s) ({reason})...")
        return llama_client.generate(follow_up)

# Global instance
intelligent_mcp = IntelligentMCPHandler()