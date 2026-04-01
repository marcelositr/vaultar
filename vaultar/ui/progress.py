from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

def create_progress():
    """Creates a rich progress bar with Braille animation."""
    return Progress(
        SpinnerColumn(spinner_name="dots"), # Dots is the Braille animation
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    )
