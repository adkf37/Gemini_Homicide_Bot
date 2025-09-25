#!/usr/bin/env python3
"""
Local LLM with MCP Tools - Main Application
"""

import sys
from typing import Optional
import argparse

from llama_client import LlamaClient
from config import config
from mcp_integration import mcp_integration
from intelligent_mcp import intelligent_mcp

class LocalLLMApp:
    """Main application class for Local LLM with MCP tools."""
    
    def __init__(self):
        self.llama_client = LlamaClient()
        print("✅ Local LLM application initialized")
        print("🔧 MCP tools available for homicide data queries")

    def ask_question(self, question: str, temperature: Optional[float] = None) -> str:
        """Ask a question using base model only."""
        temperature = temperature or config.get('model.temperature', 0.7)
        print("🤖 Using base model")
        return self.llama_client.generate(prompt=question, temperature=temperature)

    def ask_question_with_mcp(self, question: str, temperature: Optional[float] = None):
        """Ask a question that can use MCP tools intelligently."""
        # Pass temperature through to the intelligent MCP handler.
        # The handler can optionally return an interaction trace when requested.
        trace_or_response = intelligent_mcp.handle_question_with_tools(
            question,
            self.llama_client,
            include_trace=True,
        )

        if isinstance(trace_or_response, dict):
            final_answer = trace_or_response.get("final_answer", "")
            return final_answer, trace_or_response

        # Fallback for unexpected non-trace responses.
        fallback_answer = str(trace_or_response)
        return fallback_answer, {"final_answer": fallback_answer}

    def interactive_mode(self):
        """Run the application in interactive mode."""
        print("🚀 Local LLM with MCP Tools")
        print(f"📱 Model: {self.llama_client.model_name}")
        print("🔧 MCP tools available for homicide data queries")
        print("\n💡 Ask questions naturally - the system will automatically use tools when needed!")
        print("   Examples: 'What location had the most homicides?', 'How many homicides in 2023?'")
        print("\n📋 Commands:")
        print("   /help - Show help")
        print("   /mcp-tools - Show available MCP tools")  
        print("   /mcp <tool> [args] - Manual tool call")
        print("   /notools <question> - Use base model without tools")
        print("   /quit - Exit")
        print("\n" + "="*60)
        
        current_temp = config.get('model.temperature', 0.7)
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                    
                # Handle commands
                if user_input.startswith('/'):
                    parts = user_input.split(' ', 1)
                    command = parts[0].lower()
                    
                    if command == '/help':
                        self._show_help()
                    
                    elif command == '/config':
                        print(f"\nCurrent Configuration:")
                        print(f"  Model: {config.get('model.name')}")
                        print(f"  Temperature: {current_temp}")
                        print(f"  Max tokens: {config.get('model.max_tokens')}")
                        print(f"  Top-p: {config.get('model.top_p')}")
                    
                    elif command == '/temp':
                        if len(parts) > 1:
                            try:
                                new_temp = float(parts[1])
                                if 0.0 <= new_temp <= 2.0:
                                    current_temp = new_temp
                                    print(f"🌡️  Temperature set to {current_temp}")
                                else:
                                    print("❌ Temperature must be between 0.0 and 2.0")
                            except ValueError:
                                print("❌ Invalid temperature value")
                        else:
                            print(f"Current temperature: {current_temp}")
                    
                    elif command == '/mcp-tools':
                        tools = intelligent_mcp.get_tools()
                        print("\n🔧 Available MCP Tools:")
                        for tool in tools:
                            params = tool.get("parameters", {})
                            param_str = ", ".join(params.keys()) if params else "no parameters"
                            print(f"  • {tool['name']} ({param_str}): {tool['description']}")
                    
                    elif command == '/mcp':
                        if len(parts) > 1:
                            # Manual MCP tool call
                            mcp_parts = parts[1].split(' ', 1)
                            tool_name = mcp_parts[0]
                            args_str = mcp_parts[1] if len(mcp_parts) > 1 else ''
                            
                            try:
                                if args_str:
                                    # Simple argument parsing
                                    args = {}
                                    if args_str.isdigit():
                                        # Single number argument, assume it's year
                                        args = {"year": int(args_str)}
                                    else:
                                        # String argument, assume it's location_query
                                        args = {"location_query": args_str}
                                else:
                                    args = {}
                                    
                                print(f"🔧 Calling MCP tool: {tool_name}")
                                result = mcp_integration.call_tool(tool_name, args)
                                formatted_result = mcp_integration.format_tool_result(result)
                                print(f"\n📋 **MCP Result:**\n{formatted_result}")
                            except Exception as e:
                                print(f"❌ Error calling tool: {e}")
                        else:
                            print("❌ Please provide a tool name")
                            print("Usage: /mcp <tool_name> [arguments]")
                            print("Use /mcp-tools to see available tools")
                    
                    elif command == '/notools':
                        if len(parts) > 1:
                            question = parts[1]
                            print(f"🤔 Question: {question}")
                            response = self.ask_question(question, temperature=current_temp)
                            print(f"🤖 Assistant: {response}")
                        else:
                            print("❌ Please provide a question")
                    
                    else:
                        print(f"❌ Unknown command: {command}")
                        print("Type /help for available commands")
                        
                else:
                    # Default: Try intelligent MCP for homicide-related questions
                    print(f"🤔 Question: {user_input}")
                    
                    # Check if this seems like a homicide data question
                    homicide_keywords = ['homicide', 'murder', 'killing', 'crime', 'arrest', 'location', 'year', 'statistics', 'iucr', 'police', 'data', 'how many', 'what location', 'which', 'ward', 'district', 'community area', 'domestic', 'from', 'to', 'where arrests', 'no arrests', 'arrests made']
                    
                    if any(keyword in user_input.lower() for keyword in homicide_keywords):
                        print("🧠 Detected data question - using intelligent MCP...")
                        response = self.ask_question_with_mcp(user_input)
                    else:
                        response = self.ask_question(user_input, temperature=current_temp)

                    if isinstance(response, tuple):
                        answer_text, _trace = response
                    else:
                        answer_text = response

                    print(f"🤖 Assistant: {answer_text}")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def _show_help(self):
        """Show help information."""
        print("\n" + "="*60)
        print("📖 HELP - Local LLM with MCP Tools")
        print("="*60)
        print("💬 NATURAL QUESTIONS:")
        print("   Just type your question naturally!")
        print("   • 'What location had the most homicides?'")
        print("   • 'How many homicides were there in 2023?'")
        print("   • 'Show me arrest statistics'")
        print("   • 'What does IUCR mean?'")
        print("   • 'Find homicides on Michigan Avenue'")
        print()
        print("📋 COMMANDS:")
        print("   /help           - Show this help")
        print("   /config         - Show current configuration")
        print("   /temp <value>   - Set temperature (0.0-2.0)")
        print("   /mcp-tools      - List available MCP tools")
        print("   /mcp <tool>     - Manual tool call")
        print("   /notools <q>    - Ask without tools (base model only)")
        print("   /quit           - Exit application")
        print()
        print("🔧 AVAILABLE MCP TOOLS:")
        tools = intelligent_mcp.get_tools()
        for tool in tools:
            print(f"   • {tool['name']}: {tool['description']}")
        print("="*60)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Local LLM with MCP Tools")
    parser.add_argument("--setup", action="store_true", help="Run setup mode")
    parser.add_argument("--question", "-q", type=str, help="Ask a single question")
    
    args = parser.parse_args()
    
    app = LocalLLMApp()
    
    if args.setup:
        print("🛠️ Setup mode - ensuring model is available...")
        # Model availability is checked in LlamaClient.__init__
        print("✅ Setup complete")
        return
    
    if args.question:
        print(f"🤔 Question: {args.question}")
        
        # Check if this is a homicide data question
        homicide_keywords = ['homicide', 'murder', 'killing', 'crime', 'arrest', 'location', 'year', 'statistics', 'iucr', 'ward', 'district', 'community area', 'domestic', 'from', 'to', 'where arrests', 'no arrests', 'arrests made']
        if any(keyword in args.question.lower() for keyword in homicide_keywords):
            response = app.ask_question_with_mcp(args.question)
        else:
            response = app.ask_question(args.question)
            
        print(f"🤖 Assistant: {response}")
        return
    
    # Run in interactive mode
    app.interactive_mode()

if __name__ == "__main__":
    main()
