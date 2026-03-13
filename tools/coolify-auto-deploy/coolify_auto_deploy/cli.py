"""CLI for coolify-auto-deploy."""
import click
from rich.console import Console

console = Console()


@click.group()
def cli():
    """Coolify auto-deploy webhook service."""
    pass


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to listen on")
def serve(host, port):
    """Start the webhook server."""
    from .config import settings
    import uvicorn

    uvicorn.run(
        "coolify_auto_deploy.main:app",
        host=host or settings.host,
        port=port or settings.port,
        reload=False,
    )


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="JSON output")
def status(as_json):
    """Show deployment registry status."""
    import asyncio
    from .database import get_all_projects

    async def _run():
        projects = await get_all_projects()
        if as_json:
            import json

            click.echo(
                json.dumps(
                    [p.model_dump(mode="json") for p in projects], default=str
                )
            )
        else:
            from rich.table import Table

            table = Table(title="Deployed Projects")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Services")
            table.add_column("Databases")
            for p in projects:
                table.add_row(
                    p.project_name,
                    p.project_type,
                    ", ".join(p.services.keys()),
                    ", ".join(p.database_ids.keys()),
                )
            console.print(table)

    asyncio.run(_run())


@cli.command()
@click.argument("repo")
@click.option("--branch", default="main", help="Branch to deploy")
def deploy(repo, branch):
    """Manually trigger deployment for a repo."""
    import asyncio
    from .main import fetch_config, provision_new_project
    from . import coolify as coolify_mod
    from . import database as db

    async def _run():
        name = repo.split("/")[-1]
        config = await fetch_config(repo, branch)
        if not config:
            console.print("[red]No coolify-config.json found[/red]")
            raise SystemExit(1)

        record = await db.get_project(name)
        if not record:
            console.print("[yellow]New project, provisioning...[/yellow]")
            record = await provision_new_project(name, repo, config)

        env = "production" if branch == "main" else "staging"
        await coolify_mod.deploy_environment(record, env)
        console.print(f"[green]Deployed {name} ({env})[/green]")

    asyncio.run(_run())
