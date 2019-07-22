#!/usr/bin/env python
'''
    This testWrite.py file is a testcase for python-nonblock Copyright (c) 2015, 2016, 2017, 2019 Timothy Savannah.

    The testcase itself is hereby granted access as a Public Domain work, or the closest legally in your area.

    This tests the various priority levels of BackgroundWrite and gives output based on results.

    You can use this to experiment with different values and priority levels on your hardware and use cases.

    It will perform some math/memory operations whilst writing 2 files using chains at the same time.
    The result will give how long it took to write, how many calculations could be performed in that time, and an
    "interactivity score". The interactivity score is the number of calculations divided by the time you spent writing.
    The higher the ioPrio, the higher the interactivity score should be. It is a measure of how much OTHER work got done while you were
    performing otherwise blocking I/O operations.

    You may consider having a "normal" background workload going before running this test, so you can guage for yourself
      what interactivity level to choose with BackgroundWrite depending on if you want to maximize throughput of your write,
      or cpu-bound / other processes.

    There is a "DO_SYNC" option, that if True will cause the drive to flush all data to disk. You may want to play with this on
    and off. For example, if you are running a dd if=/dev/urandom of=testfile bs=512 to simulate background I/O on the same device,
    it will flush both datasets. This is moreso intended to be set to True when NO background I/O is going.
'''

import os
import time
import sys
import subprocess
import tempfile

from nonblock import bgwrite, bgwrite_chunk


class dummy(object):
    '''
        for mocking out objects
    '''
    pass


# TODO: Use os.linesep instead of explicit '\n' ?

# Generate a big file

# Set to True to sync ALL I/O (this process and others) to disk before each test.
#  This should be True if no background I/O is being ran, and maybe True maybe False if some is running.
#  It will make tests more "fair" between eachother, but with various background tasks it may introduce
#  a large variance and margin of error.
DO_SYNC = True

def printUsage():
    sys.stderr.write('''Usage: %s (Optional: [start prio] [end prio])
  Runs through priority levels, either specified start/end (inclusive), or if no args provided, the full set 1-9.

If specified, start prio must be <= end prio,
start prio must be >= 1,
end prio must be <= 9.

Tests interactivity by performing math during two sets of simultaneous bgwrites
''' %(os.path.basename(__file__), )
)
    sys.stderr.flush()

if __name__ == '__main__':

    if '--help' in sys.argv:
        printUsage()
        sys.exit(0)

    if len(sys.argv) not in (1, 3):
        sys.stderr.write('Invalid arguments.\n\n')
        printUsage()
        sys.exit(1)

    if len(sys.argv) == 3:
        ## They have provided a start and end priority

        # Validate they are integers
        if not sys.argv[1].isdigit() and not sys.argv[2].isdigit():
            sys.stderr.write('Right number of arguments, but not whole integers.\n\n')
            printUsage()
            sys.exit(1)

        # Extract priorities to test from arguments
        startPrio = int(sys.argv[1])
        endPrio = int(sys.argv[2])

        # Validate these are valid priorities, and in valid order
        if startPrio > endPrio:
            sys.stderr.write('Start priority is greater than end priority, impossible!\n\n')
            printUsage()
            sys.exit(1)

        if startPrio < 1:
            sys.stderr.write('Start priority must be >= 1\n\n')
            printUsage()
            sys.exit(1)

        if endPrio > 9:
            sys.stderr.write('End priority must be <= 9\n\n')
            printUsage()
            sys.exit(1)

    else:

        print ( 'No arguments provided, defaulting to testing full set (1-9 inclusive) of IO priorities\n' )

        startPrio = 1
        endPrio = 9



    ## Generate a fairly large dataset

    bigFile = tempfile.NamedTemporaryFile(mode='wt')
    # Write some data
    numLetters = ord('z') - ord('a')
    lettersLst = [ chr( ord('a') + i ) for i in range(numLetters) ]
    lettersStr = ''.join(lettersLst)
    curLen = 0
    before = time.time()
    # Size of my libc at time of writing
    while curLen < 2317344:
        bigFile.write(lettersStr)
        curLen += numLetters

    # Try to force flush
    try:
        bigFile.flush()
    except:
        pass
    after = time.time()

    print ( 'Generated %d bytes of data in %.5f seconds.' %( curLen, after - before ) )

    bigFilename = bigFile.name

    currentDirectory = os.path.abspath( os.path.dirname( __file__ ) )
    baseFilename = os.path.basename( __file__ )
    print ( 'Using containing directory of this file [ %s ] for writes...\n' %( currentDirectory, ) )

    # Change dir to this directory, so we don't have to use os.sep
    os.chdir(currentDirectory)

    username = os.environ['USER']

    # Some values used for the math
    x = 13
    y = 37

    # Get some big data - open a fresh copy so we aren't reading from buffer
    with open(bigFilename, 'rb') as f:
        before = time.time()
        data = f.read()
        after = time.time()

    print ('Time to read %d bytes: %f\n' %(len(data), after - before,) )

    print ( 'Running through IO priorities, %d -> %d (inclusive),\n  whilst running simultaneous math calculations to test interactivity\n  and I/O rate at each level...\n\n%s\n\n' %( startPrio, endPrio, '-' * 50, ) )

    # Expand that big data
    data = data * 50

    dataLen = len(data)

    # Iterate through the I/O priorities, do the operation, and show the score.
    for ioPrio in range(startPrio, endPrio + 1, 1):
        answers = [22]
        answers2 = [16]
        answers3 = [81]
        if os.path.exists('nb_test_output1'):
            os.unlink('nb_test_output1')
        if os.path.exists('nb_test_output2'):
            os.unlink('nb_test_output2')
        f = open('nb_test_output1', 'wb')
        f2 = open('nb_test_output2', 'wb')

        if DO_SYNC is True:
            # Ensure pending data is flushed so next run has fair chance
            if sys.version_info.major >= 3:
                # python3 supports os.sync
                os.sync()
            elif sys.platform == 'linux':
                # python2 has no sync, but if we are on linux we can try
                #   the sync command
                try:
                    pipe = subprocess.Popen('sync', shell=True)
                    pipe.wait()
                except:
                    pass
            time.sleep(3)


        before = time.time()
        # Start first chain, final will close f1
        obj1 = bgwrite(f, data,  ioPrio=ioPrio)
        obj2 = bgwrite(f, data,  chainAfter=obj1, ioPrio=ioPrio)
        obj3 = bgwrite_chunk(f, data,  len(data) / 4, chainAfter=obj2, ioPrio=ioPrio)
        lastObj = obj4 = bgwrite(f, data,  chainAfter=obj3, closeWhenFinished=True, ioPrio=ioPrio)

        # Start second chain, final will close f2
        objy1 = bgwrite_chunk(f2, data, len(data) / 4, ioPrio=ioPrio)
        objy2 = bgwrite(f2, data, chainAfter=objy1, ioPrio=ioPrio)
        objy3 = bgwrite(f2, data, chainAfter=objy2, ioPrio=ioPrio)
        lastObjy = objy4 = bgwrite(f2, data, chainAfter=objy3, closeWhenFinished=True, ioPrio=ioPrio)

        # While the writing is going on, start doing some calculations
        while lastObj.finished is False or lastObjy.finished is False:
            i = 0
            while i < 7 and (lastObj.finished is False or lastObjy.finished is False):
                answers.append(x * y * (i*i))
                answers2.append((x - y) * pow(i, 4))
                answers3.append(x + y + (i/2.0))
    #        time.sleep(.000001)

        # Writing stopped, take stock.
        after = time.time()

        numAnswers = len(answers) + len(answers2) + len(answers3) - 3
        delta = round(after - before, 5)

        sys.stdout.write(('-' * 50) + '\n')
        sys.stdout.write('[%d] Time to write: %f seconds\n' %(ioPrio, delta) )
        sys.stdout.write('[%d] Number of answers generated during writes: %d\n' %(ioPrio, numAnswers) )
        sys.stdout.write('[%d] Average write speed: %f M/s\n' %(ioPrio, round((dataLen / delta) / (1024.0 * 1024.0), 5) ) )
        sys.stdout.write('[%d] Interactivity score: %f\n' % (ioPrio, round(numAnswers / delta, 5)) )
        sys.stdout.write(('=' * 50) + '\n\n')
        sys.stdout.flush()



    print ( 'Cleaning-up')

    if os.path.exists('nb_test_output1'):
        os.unlink('nb_test_output1')
    if os.path.exists('nb_test_output2'):
        os.unlink('nb_test_output2')

    # Cleanup the generated data
    bigFile.close()

# vim: set ts=4 st=4 sw=4 expandtab :
