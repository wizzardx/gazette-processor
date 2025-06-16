#!/bin/env python

from pathlib import Path

import click
from icecream import ic

from src.ongoing_convo_with_bronn_2025_06_10.utils import output_testing_bulletin
from src.ongoing_convo_with_bronn_2025_06_10.utils_2 import output_testing_bulletin_2

ic.configureOutput(includeContext=True)


@click.group()
def cli() -> None:
    """Government gazette notice processing system."""
    pass


GG_DIR = Path(
    "/home/david/dev/misc/bronnwyn-stuff/bulletin-generator-rnd/files_from_bronnwyn/2025-05-28/David Bulletin/Source GGs/2025/"
)


@cli.command()
def bulletin2() -> None:
    """Generate a testing bulletin using all available Gazette PDF files."""
    output_testing_bulletin_2(gg_dir=GG_DIR)


@cli.command()
def bulletin() -> None:
    """Generate a testing bulletin from notices.csv."""
    output_testing_bulletin(gg_dir=GG_DIR)


if __name__ == "__main__":
    cli()
