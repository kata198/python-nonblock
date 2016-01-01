'''
    Copyright (c) 2015 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    BackgroundWrite.py Contains pure-python functions for non-blocking background writing (writing multiple streams at once; interactive writing allowing a high amount of CPU time for calculations/other tasks


'''
# vim: ts=4 sw=4 expandtab

#import sys
import threading
import time

from collections import deque

__all__ = ('BackgroundWriteProcess', 'BackgroundIOPriority', 'bgwrite', 'bgwrite_chunk', 'chunk_data')

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

    __slots__ = ('chainPollTime', 'defaultChunkSize', 'priorityPct', 'charityRate', 'charityTime')

    def __init__(self, chainPollTime, defaultChunkSize, priorityPct, charityRate=1.85, charityTime=.0003):
        '''
            __init__ - Create a BackgroundIOPriority. 

            Some terms: throughput - Bandwidth out (Megs per second)
                        interactivity - CPU time available for other tasks (calculations, other I/O, etc)

            @param chainPollTime - float > 0, When chaining, this is the sleep time between checking if prior is finished.
                Too low and the polling takes up CPU time, too high and you'll lose a little time in between chained writes, while gaining interactivity elsewhere.

            @param defaultChunkSize - integer > 0, When providing a straight string/bytes to bgwrite (instead of chunking yourself, or using bgwrite_chunk) this will
                be used as the max size of each chunk. Each chunk is written and a flush is issued (if the stream supports it).
                Increasing this increases throughput while decreasing interactivity

            @param priorityPct - integer > 0, generally 0-100. When this number is high, throughput for the operation will be higher. When it is lower,
               interactivity is higher, e.x. if you have a calculation going and a write going, the lower this number the longer the write will take, but the more
               calculations will be performed during that period.

            @param charityRate - float >= 0, Every couple of blocks written, the current throughput is checked and if things have been going swiftly
               a short sleep will be incurred. Increasing this number causes that check to happen more often.

               This number is related to both the number of blocks and the priorityPct. The default, should be fine, but you may find it better
               as a different value in certain cases. Increasing or decreasing could either increase or decrease interactivity, depending on those other factors.
               Generally, however, increasing this increases interactivity and ability to write in parallel, at the cost of throughput.

            @param charityTime - float >= 0 - Used to calculate the time to sleep when the charity period hits. The equation is:
                sleepTime = charityTime * ((dataWritten / delta) / ( (dataWritten / delta) * priorityPctDec))
                 Where dataWritten = number of bytes written already, delta = total time spent writing (not including charity time sleeping)
                 and priorityPctDec = priorityPct / 100.

                 Increasing this can increase interactivity and allow more parallel operations at the cost of throughput.
                 The default should be fine for the majority of cases, but it is tunable.

            An "interactivity score" is defined to be (number of calculations) / (time to write data).
        '''


        self.chainPollTime = chainPollTime
        self.defaultChunkSize = defaultChunkSize
        self.priorityPct = float(priorityPct)
        self.charityRate = float(charityRate)
        self.charityTime = float(charityTime)

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
    1  : BackgroundIOPriority(.0009, _SIZE_MEG * 5,    100), # Most throughput, least interactivity, but still very interactive.
    2  : BackgroundIOPriority(.0009, _SIZE_MEG * 4,     90),
    3  : BackgroundIOPriority(.0015, _SIZE_MEG * 3,     80),
    4  : BackgroundIOPriority(.0015, _SIZE_MEG * 2,     70),
    5  : BackgroundIOPriority(.0019, _SIZE_MEG * 1.25,  65),
    6  : BackgroundIOPriority(.0019, _SIZE_MEG * .6,   50),
    7  : BackgroundIOPriority(.0024, _SIZE_MEG * .4,    40),
    8  : BackgroundIOPriority(.0024, _SIZE_MEG * .25,   30),
    9  : BackgroundIOPriority(.0031, _SIZE_MEG * .175,  30),
    10 : BackgroundIOPriority(.0100, _SIZE_MEG * .1,    25), # Least throughput, most interactivity, very little throughput
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
        priorityPct = self.backgroundIOPriority.priorityPct
        priorityPctDec = priorityPct / 100.0

        charityRate = self.backgroundIOPriority.charityRate
        charityTime = self.backgroundIOPriority.charityTime

        # Number of blocks, total
        numBlocks = len(self.remainingData)
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


        # charityPeriod - How often we stop for a short bit to be gracious to other running tasks
        charityPeriod = int(max( (priorityPctDec * numBlocks) / charityRate, 3 ))

        # i will be the counter from 1 to charityPeriod, and then reset
        i = 1

        # Before represents the "start" time. When we sleep, we will increment this value
        #  such that [ delta = (after - before) ] only accounts for time we've spent writing,
        #  not in charity.
        before = time.time()
        while len(self.remainingData) > 0:

            # pop, write, flush
            nextData = self.remainingData.popleft()
            fileObj.write(nextData)
            doFlush(fileObj)
            
            dataWritten += len(nextData)
            
            if i == charityPeriod:
                # We've completed a full period, time for charity
                after = time.time()

                delta = after - before
                # Uncomment the following to see rates

#                sys.stdout.write('\t  I have written %d bytes in %3.3f seconds (%4.5f M/s)\n' %(dataWritten, delta, (dataWritten / delta) / (1024*1024)  ))
#                sys.stdout.flush()

                # Calculate how much time we should give up to others
                sleepTime = charityTime * ((dataWritten / delta) / ( (dataWritten / delta) * priorityPctDec))
#                sys.stdout.write('DOING sleepTime is: %f\n' %(sleepTime,))
                time.sleep(sleepTime)

                # Adjust so that [ delta = (after - before) ] only reflects time spent writing, and reset counter
                before += (time.time() - after)
                i = 0

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

