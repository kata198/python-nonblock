'''
    Copyright (c) 2015, 2016, 2017 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    BackgroundWrite.py Contains pure-python functions for non-blocking background writing (writing multiple streams at once; interactive writing allowing a high amount of CPU time for calculations/other tasks


'''
# vim: ts=4 sw=4 expandtab

import threading
import time

from collections import deque

# TODO: I'd like to maybe remove defaultChunkSize from BACKGROUND_IO_PRIO and instead keep it strictly priority,
#  and forcing chunk size to be specified every time (basically, making "bgwrite_chunk" the prototype ).
#
#  See "remove_default_chunk_size.patch" in the default directory. The issue I have with this is there
#    seems to be a noticable drop in performance with this applied, and the priority levels have
#    much less meaning.


__all__ = ('BackgroundWriteProcess', 'BackgroundIOPriority', 'bgwrite', 'bgwrite_chunk', 'chunk_data')

# Uncomment the "DEBUG" sections you want to see below. Search for DEBUG.
#DEBUG = False
#if DEBUG:
#    import sys


def bgwrite(fileObj, data, closeWhenFinished=False, chainAfter=None, ioPrio=4):
    '''
        bgwrite - Start a background writing process

            @param fileObj <stream> - A stream backed by an fd

            @param data    <str/bytes/list> - The data to write. If a list is given, each successive element will be written to the fileObj and flushed. If a string/bytes is provided, it will be chunked according to the #BackgroundIOPriority chosen. If you would like a different chunking than the chosen ioPrio provides, use #bgwrite_chunk function instead.

               Chunking makes the data available quicker on the other side, reduces iowait on this side, and thus increases interactivity (at penalty of throughput).

            @param closeWhenFinished <bool> - If True, the given fileObj will be closed after all the data has been written. Default False.

            @param chainAfter  <None/BackgroundWriteProcess> - If a BackgroundWriteProcess object is provided (the return of bgwrite* functions), this data will be held for writing until the data associated with the provided object has completed writing.
            Use this to queue several background writes, but retain order within the resulting stream.


            @return - BackgroundWriteProcess - An object representing the state of this operation. @see BackgroundWriteProcess
    '''

    thread = BackgroundWriteProcess(fileObj, data, closeWhenFinished, chainAfter, ioPrio)
    thread.start()

    return thread

def bgwrite_chunk(fileObj, data, chunkSize, closeWhenFinished=False, chainAfter=None, ioPrio=4):
    '''
        bgwrite_chunk - Chunk up the data into even #chunkSize blocks, and then pass it onto #bgwrite.
            Use this to break up a block of data into smaller segments that can be written and flushed.
            The smaller the chunks, the more interactive (recipient gets data quicker, iowait goes down for you) at cost of throughput.

            bgwrite will automatically chunk according to the given ioPrio, but you can use this for finer-tuned control.

            @see bgwrite

        @param data <string/bytes> - The data to chunk up

        @param chunkSize <integer> - The max siZe of each chunk.
    '''
    chunks = chunk_data(data, chunkSize)

    return bgwrite(fileObj, chunks, closeWhenFinished, chainAfter, ioPrio)


class BackgroundIOPriority(object):
    '''
        BackgroundIOPriority - Priority Profile for doing background writes.

            See __init__ for fields
    '''

    __slots__ = ('chainPollTime', 'defaultChunkSize', 'bandwidthPct', 'numChunksRateSmoothing')

    def __init__(self, chainPollTime, defaultChunkSize, bandwidthPct, numChunksRateSmoothing=5):
        '''
            __init__ - Create a BackgroundIOPriority.

            Some terms: throughput - Bandwidth out (Megs per second)
                        interactivity - CPU time available for other tasks (calculations, other I/O, etc)

            @param chainPollTime - float > 0, When chaining, this is the sleep time between checking if prior is finished.
                Too low and the polling takes up CPU time, too high and you'll lose a little time in between chained writes, while gaining interactivity elsewhere.

            @param defaultChunkSize - integer > 0, When providing a straight string/bytes to bgwrite (instead of chunking yourself, or using bgwrite_chunk) this will
                be used as the max size of each chunk. Each chunk is written and a flush is issued (if the stream supports it).
                Increasing this increases throughput while decreasing interactivity

            @param bandwidthPct - integer > 0 and < 100. This is the percentage of overall bandwidth that this task will attempt to use.

              A high number means higher throughput at the cost of lest interactivity for other tasks, a low number means the opposite.

              So, for example, a bandwidthPct of "50" will attempt to use "50%" of the available bandwidth. Note, this does not represent theroetical
              max bandwidth, i.e. the max rate of the I/O device, but the amount of available bandwidth available to this application. For example,
              if this is given "100%", no throttling is performed. If this is given "80%", then it calculates the average time to write a single chunk,
              ( see #numChunksRateSmoothing for how many chunks are used in evaluating this average ), and sleeps for then 20% of that time at the end
              of every chunk.

            @param numChunksRateSmoothing - integer >= 1 , Default 5. This is the number of chunks which are used in calculating the current throughput rate.
              See #bandwidthPct for the other half of the story. The higher this number, the more "fair" your application will be against a constant
              rate of I/O by other applications, but the less able it may be to play fair when the external I/O is spiking.

              Also, consider that this is related to the #defaultChunkSize, as it is not a constant period of time. The default of "5" should be okay,
              but you may want to tune it if you use really large or really small chunk sizes.


            An "interactivity score" is defined to be (number of calculations) / (time to write data).
        '''


        self.chainPollTime = chainPollTime
        self.defaultChunkSize = defaultChunkSize
        self.bandwidthPct = float(bandwidthPct)
        if bandwidthPct <= 0 or bandwidthPct > 100:
            raise ValueError('Given bandwidthPct %f must be > 0 and <= 100')

        self.numChunksRateSmoothing = numChunksRateSmoothing

    def __getitem__(self, key):
        if key in BackgroundIOPriority.__slots__:
            return getattr(self, key)
        raise KeyError('Unknown key: %s\n' %(key,))

    def __setitem__(self, key, value):
        if key in BackgroundIOPriority.__slots__:
            return setattr(self, key, value)
        raise KeyError('Unknown key: %s\n' %(key,))


_SIZE_MEG = 1024 * 1024

# BG_IO_PRIOS - Predefined I/O priorities, 1-10. The lower the number, the more throughput at the cost of interactivity
BG_IO_PRIOS = {
    1  : BackgroundIOPriority(.0009, _SIZE_MEG * 5,    100), # Maximum throughput, no regard for interactivity.
    2  : BackgroundIOPriority(.0009, _SIZE_MEG * 4,     90),
    3  : BackgroundIOPriority(.0015, _SIZE_MEG * 3,     78),
    4  : BackgroundIOPriority(.0015, _SIZE_MEG * 2,     72),
    5  : BackgroundIOPriority(.0019, _SIZE_MEG * 1.6,   65),
    6  : BackgroundIOPriority(.0019, _SIZE_MEG * .75,   55),
    7  : BackgroundIOPriority(.0024, _SIZE_MEG * .69,   45),
    8  : BackgroundIOPriority(.0024, _SIZE_MEG * .5,    35),
    9  : BackgroundIOPriority(.0031, _SIZE_MEG * .3,    30),
    10 : BackgroundIOPriority(.0100, _SIZE_MEG * .25,   20), # Least throughput, most interactivity, very little throughput
}


class BackgroundWriteProcess(threading.Thread):
    '''
        BackgroundWriteProcess - A thread and data store representing a background write task. You should probably use one of the bgwrite* methods and not this directly.

        Attributes:

            remainingData  <deque> - A queue representing the data yet to be written

            startedWriting <bool>  - Starts False, changes to True when writing has started (thread has started and any pending prior chain has completed)

            finished    <bool>   - Starts False, changes to True after writing has completed, and if closeWhenFinished is True the handle is also closed.
    '''
# Design question: What about errors?

    def __init__(self, fileObj, dataBlocks, closeWhenFinished=False, chainAfter=None, ioPrio=4):
        '''
            __init__ - Create the BackgroundWriteProcess thread. You should probably use bgwrite or bgwrite_chunk instead of calling this directly.

            @param fileObj <stream> - A stream, like a file, to write into. Hopefully it supports flushing, but it is not a requirement.

            @param dataBlocks <bytes/str/list<bytes/str>> - If a list of bytes/str, those are treated as the data blocks, written in order with heuristics for interactivity in between blocks.  If bytes/str are provided not in a list form, they will be split based on the rules of the associated #ioPrio

            @param closeWhenFinished <bool> - Default False. If True, the fileObj will be closed after writing has completed.

            @param chainAfter <None/BackgroundWriteProcess> - If provided, will hold off writing until the provided BackgroundWriteProcess has completed (used for queueing multiple writes whilst retaining order)

            @param ioPrio <int/BackgroundIOPriority> - If an integer (1-10), a predefined BackgroundIOPriority will be used. 1 is highest throughput, 10 is most interactivity. You can also pass in your own BackgroundIOPriority object if you want to define a custom profile.


            @raises ValueError - If ioPrio is neither a BackgroundIOPriority nor integer 1-10 inclusive
                               - If chainAfter is not a BackgroundWriteProcess or None
        '''
        threading.Thread.__init__(self)
        self.fileObj = fileObj

        if isinstance(ioPrio, BackgroundIOPriority):
            self.backgroundIOPriority = ioPrio
        else:
            try:
                self.backgroundIOPriority = BG_IO_PRIOS[ioPrio]
            except KeyError:
                raise ValueError('Invalid ioPrio: %s. Available priority levels are: %s' %(str(ioPrio), str(list(BG_IO_PRIOS.keys()))) )

        if type(dataBlocks) not in (list, tuple):
            dataBlocks = chunk_data(dataBlocks, self.backgroundIOPriority.defaultChunkSize)
        self.remainingData = deque(dataBlocks)

        self.closeWhenFinished = closeWhenFinished

        if chainAfter and not isinstance(chainAfter, BackgroundWriteProcess):
            raise ValueError('chainAfter must be a BackgroundWriteProcess instance')

        self.chainAfter = chainAfter

        self.startedWriting = False
        self.finished = False


    def run(self):
        '''
            run - Starts the thread. bgwrite and bgwrite_chunk automatically start the thread.
        '''

        # If we are chaining after another process, wait for it to complete.
        #   We use a flag here instead of joining the thread for various reasons
        chainAfter = self.chainAfter
        if chainAfter is not None:
            chainPollTime = self.backgroundIOPriority.chainPollTime
            while chainAfter.finished is False:
                time.sleep(chainPollTime)


        # Pull class data into locals
        fileObj = self.fileObj
        bandwidthPct = self.backgroundIOPriority.bandwidthPct
        bandwidthPctDec = bandwidthPct / 100.0


        # Number of blocks, total (note: unused, removed)
        #numBlocks = len(self.remainingData)
        # Bytes written
        dataWritten = 0

        # Mark that we have started writing data
        self.startedWriting = True

        # Create a conditional lambda for flushing. I'd rather just only support flushable streams, but
        #   some unfortunatly just aren't. This should be cheaper than testing with hasattr at each iteration
        if hasattr(fileObj, 'flush'):
            doFlush = lambda obj : obj.flush()
        else:
            doFlush = lambda obj : 1


        # numChunksRateSmoothing - How often we stop for a short bit to be gracious to other running tasks.
        #  float for division below
        numChunksRateSmoothing = float(self.backgroundIOPriority.numChunksRateSmoothing)

        # i will be the counter from 1 to numChunksRateSmoothing, and then reset
        i = 1

        # We start with using max bandwidth until we hit #numChunksRateSmoothing , at which case we recalculate
        #  sleepTime. We sleep after every block written to maintain a desired average throughput based on
        #  bandwidthPct
        sleepTime = 0

        # Before represents the "start" time. When we sleep, we will increment this value
        #  such that [ delta = (after - before) ] only accounts for time we've spent writing,
        #  not in charity.
        before = time.time()

        # timeSlept - Amount of time slept, which must be subtracted from total time spend
        #  to get an accurate picture of throughput.
        timeSlept = 0

        # firstPass - Mark the first pass through, so we can get a rough calculation
        #  of speed from the first write, and recalculate after #numChunksRateSmoothing
        firstPass = True

        if bandwidthPct == 100:
            shouldRecalculate = lambda i, numChunksRateSmoothing, firstPass : False
        else:
            shouldRecalculate = lambda i, numChunksRateSmoothing, firstPass : firstPass or i == numChunksRateSmoothing


        while len(self.remainingData) > 0:

            # pop, write, flush
            nextData = self.remainingData.popleft()
            fileObj.write(nextData)
            doFlush(fileObj)

            dataWritten += len(nextData)
            if sleepTime:
                sleepBefore = time.time()

                time.sleep(sleepTime)

                sleepAfter = time.time()
                timeSlept += (sleepAfter - sleepBefore)

            if shouldRecalculate(i, numChunksRateSmoothing, firstPass) is True:
                # if not sleeptime, we are on first
                # We've completed a full period, time for charity
                after = time.time()

                delta = after - before - timeSlept


#                if DEBUG is True:
#                    rate = dataWritten / delta

#                    sys.stdout.write('\t  I have written %d bytes in %3.3f seconds and slept %3.3f sec (%4.5f M/s over %3.3fs)\n' %(dataWritten, delta, timeSlept, (rate) / (1024*1024), delta + timeSlept  ))
#                    sys.stdout.flush()

                # Calculate how much time we should give up on each block to other tasks
                sleepTime = delta * (1.00 - bandwidthPctDec)
                sleepTime /= numChunksRateSmoothing

#                if DEBUG is True:
#                    sys.stdout.write('Calculated new sleepTime to be: %f\n' %(sleepTime,))

                timeSlept = 0
                before = time.time()
                i = 0
#            elif DEBUG is True and i == numChunksRateSmoothing:
#                # When bandwidth pct is 100 (prio=1), the above DEBUG will never be hit.
#                after = time.time()
#
#                delta = after - before - timeSlept
#
#                rate = dataWritten / delta
#
#                sys.stdout.write('\t  I have written %d bytes in %3.3f seconds and slept %3.3f sec (%4.5f M/s over %3.3fs)\n' %(dataWritten, delta, timeSlept, (rate) / (1024*1024), delta + timeSlept  ))
#                sys.stdout.flush()
#
#                timeSlept = 0
#                before = time.time()
#                i = 0

            firstPass = False

            i += 1

        if self.closeWhenFinished is True:
            fileObj.close()

        self.finished = True


def chunk_data(data, chunkSize):
    '''
        chunk_data - Chunks a string/bytes into a list of string/bytes, each member up to #chunkSize in length.

        e.x.    chunk_data("123456789", 2) = ["12", "34", "56", "78", "9"]
    '''
    chunkSize = int(chunkSize)
    return [data[i : i + chunkSize] for i in range(0, len(data), chunkSize)]

