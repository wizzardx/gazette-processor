#!/bin/env python

import click
from icecream import ic

from src.ongoing_convo_with_bronn_2025_06_10.utils import output_testing_bulletin

ic.configureOutput(includeContext=True)


@click.group()
def cli():
    """Government gazette notice processing system."""
    pass


@cli.command()
def bulletin():
    """Generate a testing bulletin from notices.csv."""
    output_testing_bulletin()


if __name__ == "__main__":
    cli()
