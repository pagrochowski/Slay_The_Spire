#!/usr/bin/env python
"""
Interactive chat interface for the STS Advisor.

Usage:
    python scripts/chat.py
    
Commands:
    /new <character> [ascension]  - Start new run (e.g., /new silent 10)
    /status                       - Show current run status
    /end [victory|defeat]         - End current run
    /card <name>                  - Look up a card
    /relic <name>                 - Look up a relic
    /enemy <name>                 - Look up an enemy
    /clear                        - Clear conversation history
    /help                         - Show this help
    /quit                         - Exit
    
Anything else is sent to the LLM for advice.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.advisor import STSAdvisor


console = Console()


def print_help():
    """Print help message."""
    help_text = """
# STS Advisor Commands

## Run Management
- `/new <character> [ascension]` - Start new run (e.g., /new silent 10)
- `/status` - Show current run status
- `/end victory` or `/end defeat` - End current run
- `/add card <name>` - Add card to deck
- `/add relic <name>` - Add relic to run

## Queries
- `/card <name>` - Look up a card
- `/relic <name>` - Look up a relic
- `/enemy <name>` - Look up an enemy

## Other
- `/clear` - Clear conversation history
- `/help` - Show this help
- `/quit` or `/exit` - Exit

**Anything else is sent to the LLM for strategic advice.**
    """
    console.print(Markdown(help_text))


def main():
    """Run interactive chat."""
    console.print(Panel.fit(
        "[bold cyan]Slay the Spire Advisor[/bold cyan]\n"
        "[dim]Type /help for commands, or just ask for advice![/dim]",
        border_style="cyan"
    ))
    
    # Initialize advisor
    try:
        advisor = STSAdvisor()
        console.print("[green]✓[/green] Advisor initialized")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize advisor: {e}")
        console.print("[yellow]Make sure Ollama is running: ollama serve[/yellow]")
        return
    
    console.print("[dim]Ready for questions![/dim]\n")
    
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                parts = user_input[1:].split()
                cmd = parts[0].lower() if parts else ""
                args = parts[1:] if len(parts) > 1 else []
                
                if cmd in ("quit", "exit", "q"):
                    console.print("[dim]Goodbye![/dim]")
                    break
                
                elif cmd == "help":
                    print_help()
                
                elif cmd == "clear":
                    advisor.clear_history()
                    console.print("[dim]Conversation history cleared.[/dim]")
                
                elif cmd == "status":
                    status = advisor.get_run_status()
                    console.print(Panel(status, title="Run Status", border_style="green"))
                
                elif cmd == "new":
                    if not args:
                        console.print("[yellow]Usage: /new <character> [ascension][/yellow]")
                        continue
                    char = args[0]
                    asc = int(args[1]) if len(args) > 1 else 0
                    result = advisor.start_run(char, asc)
                    console.print(Panel(result, title="New Run", border_style="green"))
                
                elif cmd == "end":
                    victory = "victory" in " ".join(args).lower() if args else False
                    killed_by = " ".join(args) if not victory and args else None
                    result = advisor.end_run(victory, killed_by)
                    console.print(Panel(result, title="Run Ended", border_style="red" if not victory else "green"))
                
                elif cmd == "card":
                    if not args:
                        console.print("[yellow]Usage: /card <name>[/yellow]")
                        continue
                    name = " ".join(args)
                    result = advisor.query_card(name)
                    console.print(Panel(result, title=f"Card: {name}", border_style="blue"))
                
                elif cmd == "relic":
                    if not args:
                        console.print("[yellow]Usage: /relic <name>[/yellow]")
                        continue
                    name = " ".join(args)
                    result = advisor.query_relic(name)
                    console.print(Panel(result, title=f"Relic: {name}", border_style="magenta"))
                
                elif cmd == "enemy":
                    if not args:
                        console.print("[yellow]Usage: /enemy <name>[/yellow]")
                        continue
                    name = " ".join(args)
                    result = advisor.query_enemy(name)
                    console.print(Panel(result, title=f"Enemy: {name}", border_style="red"))
                
                elif cmd == "add":
                    if len(args) < 2:
                        console.print("[yellow]Usage: /add card <name> or /add relic <name>[/yellow]")
                        continue
                    add_type = args[0].lower()
                    name = " ".join(args[1:])
                    if add_type == "card":
                        result = advisor.add_card(name)
                    elif add_type == "relic":
                        result = advisor.add_relic(name)
                    else:
                        console.print("[yellow]Use: /add card <name> or /add relic <name>[/yellow]")
                        continue
                    console.print(f"[green]✓[/green] {result}")
                
                else:
                    console.print(f"[yellow]Unknown command: /{cmd}. Type /help for commands.[/yellow]")
            
            else:
                # Send to LLM for advice
                console.print("[dim]Thinking...[/dim]")
                response = advisor.chat(user_input)
                console.print(Panel(
                    Markdown(response),
                    title="[bold magenta]Advisor[/bold magenta]",
                    border_style="magenta"
                ))
        
        except KeyboardInterrupt:
            console.print("\n[dim]Use /quit to exit[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
