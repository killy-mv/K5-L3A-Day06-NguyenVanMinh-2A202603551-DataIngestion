"""Day 06 CLI entry point. Run CP3/4 first; CP5 stages use frozen artifacts."""
from __future__ import annotations
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description='Day 06 pipeline checkpoints')
    parser.add_argument('--stage', choices=['cp3', 'cp4', 'dev', 'freeze', 'test'], required=True)
    args = parser.parse_args()
    if args.stage == 'cp3':
        from .cp3 import main as go
    elif args.stage == 'cp4':
        from .cp4 import main as go
    else:
        from .cp5 import main_for_stage
        go = lambda: main_for_stage(args.stage)
    go()


if __name__ == '__main__':
    main()
