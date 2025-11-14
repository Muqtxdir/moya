"""
CLI for MOYA for Research.

Provides command-line interface for running the research paper analysis system.
"""

from pathlib import Path

import typer
from loguru import logger
from rich.console import Console

from moya_for_research.config import Settings
from moya_for_research.database import init_db, get_session
from moya_for_research.orchestrator import ResearchOrchestrator
from moya_for_research.agents import create_chat_agent
from moya_for_research.models import Paper, Summary, Synthesis

app = typer.Typer(
    name="moya-research",
    help="Multi-agent research paper analysis system using MOYA framework",
    add_completion=False,
)
console = Console(markup=True)


@app.command()
def analyze(
    papers_dir: Path = typer.Option(
        Path("papers"),
        "--papers-dir",
        "-p",
        help="Directory containing PDF research papers",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output_dir: Path = typer.Option(
        Path("data"),
        "--output-dir",
        "-o",
        help="Directory for output data and results",
        file_okay=False,
        dir_okay=True,
    ),
    db_dir: Path = typer.Option(
        Path("database"),
        "--db-dir",
        "-d",
        help="Directory for SQLite database",
        file_okay=False,
        dir_okay=True,
    ),
    ollama_url: str = typer.Option(
        "http://localhost:11434",
        "--ollama-url",
        help="Ollama API base URL",
    ),
    ollama_model: str = typer.Option(
        "gemma3:1b",
        "--ollama-model",
        "-m",
        help="Ollama model to use (gemma3:1b, llama3.2:3b, qwen3:4b)",
    ),
):
    """
    Analyze research papers using multi-agent system.

    This command:
    1. Parses PDF papers from the specified directory
    2. Generates structured summaries for each paper
    3. Creates cross-paper synthesis with themes, gaps, and future directions
    4. Generates mini-survey (<=800 words) with inline citations
    5. Stores results in SQLite database
    """
    try:
        # Update settings with CLI arguments
        settings = Settings(
            PAPERS_DIR=papers_dir,
            DATA_DIR=output_dir,
            DB_DIR=db_dir,
            OLLAMA_BASE_URL=ollama_url,
            OLLAMA_MODEL=ollama_model,
        )

        console.print("\n[bold cyan]MOYA Research Paper Analysis System[/bold cyan]")
        console.print(f"Papers directory: {papers_dir.absolute()}")
        console.print(f"Output directory: {output_dir.absolute()}")
        console.print(f"Database directory: {db_dir.absolute()}")
        console.print(f"Log directory: logs/")
        console.print(f"Ollama model: {ollama_model}\n")

        # Find PDF files
        pdf_files = list(papers_dir.glob("*.pdf"))
        if not pdf_files:
            console.print(
                f"[red]Error: No PDF files found in {papers_dir.absolute()}[/red]"
            )
            raise typer.Exit(code=1)

        console.print(f"Found {len(pdf_files)} PDF files:")
        for pdf in pdf_files:
            console.print(f"  • {pdf.name}")

        # Initialize database
        logger.info("Initializing database")
        init_db()

        # Create orchestrator and run workflow
        logger.info("Creating research orchestrator")
        orchestrator = ResearchOrchestrator()

        pdf_paths = [str(pdf) for pdf in pdf_files]

        console.print("\n[bold green]Starting analysis workflow...[/bold green]\n")

        results = orchestrator.process_papers(pdf_paths)

        # Display results
        console.print("\n[bold green]✓ Analysis complete![/bold green]\n")
        console.print(f"Papers parsed: {len(results['parsing'])}")
        console.print(f"Papers summarized: {len(results['summarization'])}")
        console.print(f"Synthesis generated: {'Yes' if results['synthesis'] else 'No'}")

        if results["errors"]:
            console.print(
                f"\n[yellow]Errors encountered: {len(results['errors'])}[/yellow]"
            )
            for error in results["errors"]:
                console.print(f"  • {error}")

        console.print("\n[bold]Results stored in:[/bold]")
        console.print(f"  Database: {settings.DATABASE_URL}")
        console.print(f"  Logs: {settings.LOG_DIR / 'trace.jsonl'}")

    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        logger.exception("Analysis failed")
        raise typer.Exit(code=1)


@app.command()
def chat(
    db_dir: Path = typer.Option(
        Path("database"),
        "--db-dir",
        "-d",
        help="Directory containing SQLite database",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    ollama_url: str = typer.Option(
        "http://localhost:11434",
        "--ollama-url",
        help="Ollama API base URL",
    ),
    ollama_model: str = typer.Option(
        "gemma3:1b",
        "--ollama-model",
        "-m",
        help="Ollama model to use (gemma3:1b, llama3.2:3b, qwen3:4b)",
    ),
):
    """
    Interactive chat to query analyzed research papers.

    Chat with the system about the analyzed papers, ask questions,
    and explore insights from summaries and synthesis.
    """
    try:
        # Update settings
        settings = Settings(
            DB_DIR=db_dir,
            OLLAMA_BASE_URL=ollama_url,
            OLLAMA_MODEL=ollama_model,
        )

        # Initialize database
        init_db()

        # Check if analysis has been done
        session = get_session()
        paper_count = session.query(Paper).count()
        summary_count = session.query(Summary).count()
        synthesis_count = session.query(Synthesis).count()
        session.close()

        console.print("\n[bold cyan]MOYA Research Assistant - Interactive Chat[/bold cyan]\n")

        if paper_count == 0:
            console.print(
                "[yellow]No analyzed papers found in the database.[/yellow]\n"
            )
            console.print(
                "Please run the analysis first:\n"
                "  [bold]moya-research analyze --papers-dir papers/[/bold]\n"
            )
            raise typer.Exit(code=0)

        # Greet user with paper information
        console.print(f"[green]Found {paper_count} analyzed paper(s) in the database:[/green]\n")

        # Get paper titles
        session = get_session()
        papers = session.query(Paper).all()
        for i, paper in enumerate(papers, 1):
            console.print(f"  {i}. {paper.title} ({paper.year})")
        session.close()

        console.print(f"\n[green]Summaries available: {summary_count}[/green]")
        console.print(f"[green]Synthesis available: {'Yes' if synthesis_count > 0 else 'No'}[/green]\n")

        # Load database contents for RAG-like context (fallback if tools fail)
        console.print("[dim]Loading database contents for context...[/dim]")
        from moya_for_research.tools import DBTools

        context_data = {
            "papers": [],
            "summaries": [],
            "synthesis": None
        }

        try:
            # Load all papers
            papers_result = DBTools.get_all_papers()
            if papers_result.get("status") == "success":
                context_data["papers"] = papers_result.get("papers", [])

            # Load all summaries
            summaries_result = DBTools.get_all_summaries()
            if summaries_result.get("status") == "success":
                context_data["summaries"] = summaries_result.get("summaries", [])

            # Load synthesis
            synthesis_result = DBTools.get_latest_synthesis()
            if synthesis_result.get("status") == "success":
                context_data["synthesis"] = synthesis_result

            logger.info(f"Loaded context: {len(context_data['papers'])} papers, "
                       f"{len(context_data['summaries'])} summaries")
        except Exception as e:
            logger.warning(f"Failed to load context data: {e}")
            context_data = None

        # Create chat agent with preloaded context
        console.print("[dim]Initializing chat agent with RAG context...[/dim]")
        chat_agent = create_chat_agent(context_data=context_data)

        console.print(
            "\n[bold]You can ask questions about the papers, summaries, or synthesis.[/bold]"
        )
        console.print("[dim]Type 'exit' or 'quit' to end the chat.[/dim]\n")

        # Chat loop
        while True:
            try:
                # Get user input
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

                if user_input.strip().lower() in ["exit", "quit", "bye"]:
                    console.print("\n[green]Thank you for using MOYA Research Assistant![/green]\n")
                    break

                if not user_input.strip():
                    continue

                # Get response from agent
                console.print("\n[bold magenta]Assistant:[/bold magenta] ", end="")
                response = chat_agent.handle_message(user_input)
                console.print(response)
                console.print()

            except KeyboardInterrupt:
                console.print("\n\n[green]Chat ended by user.[/green]\n")
                break
            except EOFError:
                console.print("\n\n[green]Chat ended.[/green]\n")
                break

    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        logger.exception("Chat failed")
        raise typer.Exit(code=1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
