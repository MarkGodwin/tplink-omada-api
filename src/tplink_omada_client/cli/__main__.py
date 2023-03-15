"""Module execution entry point"""
import sys

from . import main

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
