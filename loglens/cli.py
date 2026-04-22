import click
from loglens.parser import parse_file
from loglens.database import save_entries, get_all_entries, get_entries_by_level
from loglens.detector import run_all_detectors


@click.group()
def cli():
    """LogLens — CLI log analyzer and anomaly detector."""
    pass


@cli.command()
@click.argument("filepath")
def parse(filepath):
    """Parse a log file and save entries to the database."""
    click.echo(f"Parsing {filepath}...")
    try:
        entries = parse_file(filepath)
        if not entries:
            click.echo("No valid entries found in file.")
            return
        saved = save_entries(entries)
        click.secho(f"Successfully saved {saved} entries.", fg="green")
    except FileNotFoundError:
        click.secho(f"Error: File '{filepath}' not found.", fg="red")


@cli.command()
@click.option("--level", default=None, help="Filter by log level (INFO, ERROR, WARNING)")
def logs(level):
    """Display log entries from the database."""
    if level:
        entries = get_entries_by_level(level)
        click.echo(f"Showing {len(entries)} {level.upper()} entries:")
    else:
        entries = get_all_entries()
        click.echo(f"Showing all {len(entries)} entries:")

    if not entries:
        click.secho("No entries found.", fg="yellow")
        return

    for entry in entries:
        color = "red" if entry.level == "ERROR" else "yellow" if entry.level == "WARNING" else "white"
        click.secho(
            f"[{entry.timestamp}] {entry.level:<8} {entry.endpoint:<20} "
            f"HTTP {entry.status_code}  {entry.response_time_ms}ms",
            fg=color
        )


@cli.command()
def summary():
    """Show a summary of all log entries."""
    entries = get_all_entries()

    if not entries:
        click.secho("No entries in database.", fg="yellow")
        return

    total = len(entries)
    levels = {}
    endpoints = {}
    total_response_time = 0

    for entry in entries:
        levels[entry.level] = levels.get(entry.level, 0) + 1
        endpoints[entry.endpoint] = endpoints.get(entry.endpoint, 0) + 1
        total_response_time += entry.response_time_ms

    avg_response_time = round(total_response_time / total, 2)

    click.echo("\n" + "=" * 40)
    click.secho("  LogLens Summary", fg="cyan", bold=True)
    click.echo("=" * 40)
    click.echo(f"  Total entries:      {total}")
    click.echo(f"  Avg response time:  {avg_response_time}ms")
    click.echo("\n  Log levels:")
    for level, count in sorted(levels.items()):
        color = "red" if level == "ERROR" else "yellow" if level == "WARNING" else "white"
        click.secho(f"    {level:<10} {count}", fg=color)
    click.echo("\n  Endpoints:")
    for endpoint, count in sorted(endpoints.items()):
        click.echo(f"    {endpoint:<25} {count} requests")
    click.echo("=" * 40 + "\n")


@cli.command()
def anomalies():
    """Run anomaly detection on log entries."""
    click.echo("Running anomaly detection...")
    results = run_all_detectors()

    if "message" in results:
        click.secho(results["message"], fg="yellow")
        return

    click.echo(f"\nAnalyzed {results['total_entries_analyzed']} entries.")

    click.echo("\n--- Statistical Anomalies ---")
    if results["statistical_anomaly_count"] == 0:
        click.secho("None found.", fg="green")
    else:
        for a in results["statistical_anomalies"]:
            click.secho(f"  [ID {a['id']}] {a['endpoint']} - {a['response_time_ms']}ms", fg="red")
            click.echo(f"  Reason: {a['reason']}")

    click.echo("\n--- Isolation Forest Anomalies ---")
    if results["isolation_forest_anomaly_count"] == 0:
        click.secho("None found.", fg="green")
    else:
        for a in results["isolation_forest_anomalies"]:
            click.secho(f"  [ID {a['id']}] {a['endpoint']} - {a['response_time_ms']}ms", fg="red")
            click.echo(f"  Reason: {a['reason']}")
    click.echo()