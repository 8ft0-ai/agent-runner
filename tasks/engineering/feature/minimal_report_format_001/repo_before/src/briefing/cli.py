"""Tiny status CLI without external dependencies."""

import argparse

from .data import get_snapshot
from .formatting import render_text


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("text",), default="text")
    args = parser.parse_args(argv)
    return render_text(get_snapshot())


def main():
    print(run())


if __name__ == "__main__":
    main()
