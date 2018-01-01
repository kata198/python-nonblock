#!/usr/bin/python

import time
import sys

from nonblock import nonblock_read

if __name__ == '__main__':
    
    fname = sys.argv[1]

    with open(fname, 'rb') as f:
        t1 = time.time()
        #import pdb; pdb.set_trace()
        contents = nonblock_read(f)
        #contents = f.read()
        t2 = time.time()

    print ( "Read %d bytes in %.4f seconds." %( len(contents), round(t2 - t1, 4) ) )
