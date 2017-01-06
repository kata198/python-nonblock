#!/usr/bin/env python
'''
    This testWrite.py file is a testcase for python-nonblock (c) 2015 Tim Savannah.

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
import glob
import time
import sys
from nonblock import bgwrite, bgwrite_chunk


class dummy(object):
    '''
        for mocking out objects
    '''
    pass


# Pick a big file

# Set to True to sync ALL I/O (this process and others) to disk before each test.
#  This should be True if no background I/O is being ran, and maybe True maybe False if some is running.
#  It will make tests more "fair" between eachother, but with various background tasks it may introduce
#  a large variance and margin of error.
DO_SYNC = True

if __name__ == '__main__':

    BIG_FILE = glob.glob('/usr/lib/libc-2.*.so')[0]

    startPrio = 1
    endPrio = 10

    if len(sys.argv) == 3:
        startPrio = int(sys.argv[1])
        endPrio = int(sys.argv[2]) + 1

    username = os.environ['USER']

    # Some values used for the math
    x = 13
    y = 37
    
    # Get some big data
    with open(BIG_FILE, 'rb') as f:
        before = time.time()
        data = f.read()
        after = time.time()

    sys.stdout.write('Time to read: %f\n' %(after - before,))

    # Expand that big data
    data = data * 50

    dataLen = len(data)

    # Iterate through the I/O priorities, do the operation, and show the score.
    for ioPrio in range(startPrio, endPrio, 1):
        answers = [22]
        answers2 = [16]
        answers3 = [81]
        if os.path.exists('/home/%s/nb_test_output1' %(username,)):
            os.unlink('/home/%s/nb_test_output1' %(username,))
        if os.path.exists('/home/%s/nb_test_output2' %(username,)):
            os.unlink('/home/%s/nb_test_output2' %(username,))
        f = open('/home/%s/nb_test_output1' %(username,), 'wb')
        f2 = open('/home/%s/nb_test_output2' %(username,), 'wb')

        if DO_SYNC is True:
            # Ensure pending data is flushed so next run has fair chance
            os.sync()
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

        sys.stdout.write(('-' * 40) + '\n')
        sys.stdout.write('[%d] Time to write: %f\n' %(ioPrio, delta) )
        sys.stdout.write('[%d] Number of answers generated: %d\n' %(ioPrio, numAnswers) )
        sys.stdout.write('[%d] Average write speed: %f M/s\n' %(ioPrio, round((dataLen / delta) / (1024.0 * 1024.0), 5) ) )
        sys.stdout.write('[%d] Interactivity score: %f\n' % (ioPrio, round(numAnswers / delta, 5)) )
        sys.stdout.write(('=' * 40) + '\n\n')
        sys.stdout.flush()



    if os.path.exists('/home/%s/nb_test_output1' %(username,)):
        os.unlink('/home/%s/nb_test_output1' %(username,))
    if os.path.exists('/home/%s/nb_test_output2' %(username,)):
        os.unlink('/home/%s/nb_test_output2' %(username,))
