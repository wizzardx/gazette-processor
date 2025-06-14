#!/bin/env python

import click
from icecream import ic

from src.ongoing_convo_with_bronn_2025_06_10.utils import output_testing_bulletin
from src.ongoing_convo_with_bronn_2025_06_10.utils_2 import output_testing_bulletin_2

ic.configureOutput(includeContext=True)


@click.group()
def cli():
    """Government gazette notice processing system."""
    pass


@cli.command()
def bulletin2():
    """Generate a testing bulletin using all available Gazette PDF files."""
    output_testing_bulletin_2()


@cli.command()
def bulletin():
    """Generate a testing bulletin from notices.csv."""
    output_testing_bulletin()


if __name__ == "__main__":
    cli()
