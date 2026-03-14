import typer

app = typer.Typer(name="bd", help="Buttondown newsletter CLI.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Buttondown newsletter CLI."""
