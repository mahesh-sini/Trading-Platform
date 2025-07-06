#!/usr/bin/env python3
"""
Claude API CLI Integration for VS Code Terminal
Usage: python claude_cli.py "your prompt here"
"""

import anthropic
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Using environment variables only.")

def setup_api_key():
    """Get API key from environment or .env file"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found!")
        print("Please set it in one of these ways:")
        print("1. Create a .env file: echo 'ANTHROPIC_API_KEY=your-key-here' > .env")
        print("2. Export it: export ANTHROPIC_API_KEY='your-key-here'")
        print("3. Add to ~/.bashrc: echo 'export ANTHROPIC_API_KEY=your-key-here' >> ~/.bashrc")
        sys.exit(1)
    return api_key

def ask_claude(prompt, conversation_history=None):
    """Send prompt to Claude and get response"""
    try:
        client = anthropic.Anthropic(api_key=setup_api_key())
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": prompt})
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=messages
        )
        
        return response.content[0].text
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def save_conversation(prompt, response):
    """Save conversation to local file for context"""
    # Create conversations directory if it doesn't exist
    conversations_dir = Path("conversations")
    conversations_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = conversations_dir / f"claude_conversation_{timestamp}.json"
    
    conversation = {
        "timestamp": timestamp,
        "prompt": prompt,
        "response": response
    }
    
    with open(filename, 'w') as f:
        json.dump(conversation, f, indent=2)
    
    print(f"\n💾 Conversation saved to {filename}")

def load_context(context_file):
    """Load previous conversation for context"""
    try:
        with open(context_file, 'r') as f:
            data = json.load(f)
            return [
                {"role": "user", "content": data["prompt"]},
                {"role": "assistant", "content": data["response"]}
            ]
    except FileNotFoundError:
        return None

def main():
    if len(sys.argv) < 2:
        print("🤖 Claude CLI for Trading Platform Development")
        print("=" * 50)
        print("Usage: python claude_cli.py \"your prompt here\"")
        print("\nExamples:")
        print("python claude_cli.py \"Help me create the project structure\"")
        print("python claude_cli.py \"Generate a FastAPI endpoint for user authentication\"")
        print("python claude_cli.py \"Create a React component for the trading dashboard\"")
        print("\nOptions:")
        print("--context <file>  Load previous conversation for context")
        sys.exit(1)
    
    # Handle context loading
    context_history = None
    if "--context" in sys.argv:
        context_index = sys.argv.index("--context")
        if context_index + 1 < len(sys.argv):
            context_file = sys.argv[context_index + 1]
            context_history = load_context(context_file)
            # Remove context args from prompt
            sys.argv = sys.argv[:context_index] + sys.argv[context_index + 2:]
    
    prompt = " ".join(sys.argv[1:])
    
    print(f"🤖 Asking Claude: {prompt[:100]}...")
    print("=" * 50)
    
    response = ask_claude(prompt, context_history)
    print(response)
    
    # Optionally save conversation
    print("\n" + "=" * 50)
    save_choice = input("💾 Save this conversation? (y/n): ").lower()
    if save_choice == 'y':
        save_conversation(prompt, response)

if __name__ == "__main__":
    main()