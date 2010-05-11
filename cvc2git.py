#!/usr/bin/python

import sys

from clone import do_clone

def main():
    if not len(sys.argv) in [2, 3]:
        print "Usage: %s <trove-fullversion> [<directory>]" % sys.argv[0]
        sys.exit()

    dest = sys.argv[2] if len(sys.argv) == 3 else None
    do_clone(sys.argv[1], dest)

if __name__ == "__main__":
    main()
