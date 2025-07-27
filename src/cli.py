"""CLI interface for radio station database management."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import track
from rich.table import Table

from .database import init_db, get_connection
from .fcc_parser import FCCDataFetcher

app = typer.Typer(help="Radio Station Database CLI")
console = Console()

@app.command()
def init(
    db_path: str = typer.Option("radio_stations.db", help="Database file path")
):
    """Initialize the database with schema."""
    console.print(f"[bold blue]Initializing database at {db_path}...[/bold blue]")
    
    try:
        init_db(db_path)
        console.print("[bold green]✓ Database initialized successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Error initializing database: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def fetch(
    db_path: str = typer.Option("radio_stations.db", help="Database file path"),
    service: str = typer.Option("both", help="Service type: fm, am, or both"),
    limit: Optional[int] = typer.Option(None, help="Limit number of stations to fetch")
):
    """Fetch radio station data from FCC and store in database."""
    
    if not Path(db_path).exists():
        console.print(f"[bold red]✗ Database {db_path} does not exist. Run 'init' first.[/bold red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Fetching {service.upper()} station data...[/bold blue]")
    
    fetcher = FCCDataFetcher()
    
    try:
        all_stations = []
        
        if service in ("fm", "both"):
            console.print("Fetching FM stations...")
            fm_stations = fetcher.fetch_fm_stations()
            if limit and service == "fm":
                fm_stations = fm_stations[:limit]
            all_stations.extend(fm_stations)
            
        if service in ("am", "both"):
            console.print("Fetching AM stations...")
            am_stations = fetcher.fetch_am_stations()
            if limit and service == "am":
                am_stations = am_stations[:limit]
            all_stations.extend(am_stations)
            
        if limit and service == "both":
            all_stations = all_stations[:limit]
            
        # Store in database
        console.print(f"Storing {len(all_stations)} stations in database...")
        _store_stations(all_stations, db_path)
        
        console.print(f"[bold green]✓ Successfully stored {len(all_stations)} stations![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error fetching data: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def stats(
    db_path: str = typer.Option("radio_stations.db", help="Database file path")
):
    """Show database statistics."""
    
    if not Path(db_path).exists():
        console.print(f"[bold red]✗ Database {db_path} does not exist.[/bold red]")
        raise typer.Exit(1)
    
    try:
        conn = get_connection(db_path)
        
        # Get counts by service type
        fm_count = conn.execute("SELECT COUNT(*) FROM stations WHERE service_type = 'FM'").fetchone()[0]
        am_count = conn.execute("SELECT COUNT(*) FROM stations WHERE service_type = 'AM'").fetchone()[0]
        total_count = fm_count + am_count
        
        # Get counts by status
        status_counts = conn.execute("""
            SELECT status, COUNT(*) 
            FROM stations 
            GROUP BY status 
            ORDER BY COUNT(*) DESC
        """).fetchall()
        
        # Get top states
        state_counts = conn.execute("""
            SELECT state, COUNT(*) 
            FROM stations 
            GROUP BY state 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
        """).fetchall()
        
        conn.close()
        
        # Display statistics
        console.print(f"\n[bold blue]Radio Station Database Statistics[/bold blue]")
        console.print(f"Database: {db_path}")
        
        # Service type table
        service_table = Table(title="Stations by Service Type")
        service_table.add_column("Service", style="cyan")
        service_table.add_column("Count", style="magenta")
        
        service_table.add_row("FM", str(fm_count))
        service_table.add_row("AM", str(am_count))
        service_table.add_row("Total", str(total_count), style="bold")
        
        console.print(service_table)
        
        # Status table
        if status_counts:
            status_table = Table(title="Stations by Status")
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Count", style="magenta")
            
            for status, count in status_counts:
                status_table.add_row(status or "Unknown", str(count))
                
            console.print(status_table)
        
        # State table
        if state_counts:
            state_table = Table(title="Top 10 States by Station Count")
            state_table.add_column("State", style="cyan")
            state_table.add_column("Count", style="magenta")
            
            for state, count in state_counts:
                state_table.add_row(state, str(count))
                
            console.print(state_table)
        
    except Exception as e:
        console.print(f"[bold red]✗ Error reading database: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (call sign, city, or licensee)"),
    db_path: str = typer.Option("radio_stations.db", help="Database file path"),
    limit: int = typer.Option(10, help="Maximum results to show")
):
    """Search for radio stations."""
    
    if not Path(db_path).exists():
        console.print(f"[bold red]✗ Database {db_path} does not exist.[/bold red]")
        raise typer.Exit(1)
    
    try:
        conn = get_connection(db_path)
        
        # Search across call_sign and city
        results = conn.execute("""
            SELECT call_sign, frequency, service_type, city, state
            FROM stations 
            WHERE call_sign LIKE ? 
               OR city LIKE ?
            ORDER BY call_sign
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        
        conn.close()
        
        if not results:
            console.print(f"[yellow]No stations found matching '{query}'[/yellow]")
            return
            
        # Display results
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("Call Sign", style="cyan")
        table.add_column("Frequency", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Location", style="yellow")
        
        for row in results:
            call_sign, freq, service_type, city, state = row
            freq_str = f"{freq:.1f} MHz" if service_type == "FM" else f"{freq:.0f} kHz"
            location = f"{city}, {state}"
            
            table.add_row(call_sign, freq_str, service_type, location)
            
        console.print(table)
        console.print(f"[dim]Showing {len(results)} of maximum {limit} results[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error searching database: {e}[/bold red]")
        raise typer.Exit(1)

def _store_stations(stations, db_path: str):
    """Store stations in database."""
    conn = get_connection(db_path)
    
    for station in track(stations, description="Storing stations..."):
        try:
            conn.execute("""
                INSERT OR REPLACE INTO stations (
                    call_sign, facility_id, service_type, frequency,
                    station_name, city, state, latitude, longitude,
                    power_watts, status, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                station.call_sign,
                station.facility_id,
                station.service_type,
                station.frequency,
                None,  # station_name not parsed yet
                station.city,
                station.state,
                station.latitude,
                station.longitude,
                station.power_watts,
                station.status,
                f"FCC_{station.service_type}"
            ))
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to store {station.call_sign}: {e}[/yellow]")
            continue
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    app()