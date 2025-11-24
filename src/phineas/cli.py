import sys
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    # Reconfigure stdout and stderr to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from phineas.agent import Agent
from phineas.utils.intro import print_intro
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

def main():
    print_intro()
    agent = Agent()

    # Create a prompt session
    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
          # Prompt the user for input
          query = session.prompt(">> ")
          if query.lower() in ["exit", "quit"]:
              print("Goodbye!")
              break
          if query:
              # Run the agent
              agent.run(query)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
