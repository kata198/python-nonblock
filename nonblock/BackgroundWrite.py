'''
    Copyright (c) 2015 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    BackgroundWrite.py Contains pure-python functions for non-blocking background writing


'''
# vim: ts=4 sw=4 expandtab

import select
import threading
import time
import sys

from collections import deque

__all__ = ('BackgroundWriteProcess', 'bgwrite', 'bgwrite_chunk', 'chunk_data')

class BackgroundWriteProcess(threading.Thread):
    '''
        BackgroundWriteProcess - A thread and data store representing a background write task. You should probably use one of the bgwrite* methods and not this directly.

        Attributes:

            remainingData  <deque> - A queue representing the data yet to be written

            startedWriting <bool>  - Starts False, changes to True when writing has started (thread has started and any pending prior chain has completed)

            doneWriting    <bool>   - Starts False, changes to True after writing has completed, and if closeWhenFinished is True the handle is also closed.
    '''
# Design question: What about errors?

    CHAIN_POLL_TIME = .02
    DATA_BLOCK_REST_TIME = .000001 # Time to rest in between data blocks. A small sleep adds interactivity
    DEFAULT_CHUNK_SIZE = 4096


    def __init__(self, fileObj, dataBlocks, closeWhenFinished=False, chainAfter=None):
        threading.Thread.__init__(self)
        self.fileObj = fileObj

        if type(dataBlocks) not in (list, tuple):
            dataBlocks = chunk_data(dataBlocks, self.DEFAULT_CHUNK_SIZE)
        self.remainingData = deque(dataBlocks)

        self.closeWhenFinished = closeWhenFinished

        if chainAfter and not isinstance(chainAfter, BackgroundWriteProcess):
            raise ValueError('chainAfter must be a BackgroundWriteProcess instance')

        self.chainAfter = chainAfter

        self.startedWriting = False
        self.doneWriting = False


    def run(self):
        if self.chainAfter is not None:
            while self.chainAfter.doneWriting is False:
                time.sleep(self.CHAIN_POLL_TIME)


        # TODO: refactor this block rest time a bit
        blockRestTime = self.DATA_BLOCK_REST_TIME
        selectTimeout = blockRestTime * 3
        fileObj = self.fileObj

        self.startedWriting = True

        while len(self.remainingData) > 0:
            (junk, readyToWrite, junk) = select.select([], [fileObj], [], selectTimeout)
            if readyToWrite:
                nextData = self.remainingData.popleft()
                fileObj.write(nextData)
                if hasattr(fileObj, 'flush'):
                    fileObj.flush()
#            time.sleep(blockRestTime)

        if self.closeWhenFinished is True:
            fileObj.close()

        self.doneWriting = True


def chunk_data(data, chunkSize):
    '''
        chunk_data - Chunks a string/bytes into a list of string/bytes, each member up to #chunkSize in length.

        e.x.    chunk_data("123456789", 2) = ["12", "34", "56", "78", "9"]
    '''
    return [data[i : i + chunkSize] for i in range(0, len(data), chunkSize)]

def bgwrite(fileObj, data, closeWhenFinished=False, chainAfter=None):
    '''
        bgwrite - Start a background writing process

            @param fileObj <stream> - A stream backed by an fd

            @param data    <str/bytes/list> - The data to write. If a list is given, each successive element will be written to the fileObj and flushed. If a string/bytes is provided, it will be chunked to the default size (4096)
               This makes the data available quicker on the other side, reduces iowait on this side, and thus increases interactivity (at penalty of throughput).
               If you want to write in one big block for some reason, make your bytes/str into a list.

            @param closeWhenFinished <bool> - If True, the given fileObj will be closed after all the data has been written. Default False.

            @param chainAfter  <None/BackgroundWriteProcess> - If a BackgroundWriteProcess object is provided (the return of bgwrite* functions), this data will be held for writing until the data associated
                with the provided object has completed writing. Use this to queue several background writes, but retain order within the resulting stream.


            @return - BackgroundWriteProcess - An object representing the state of this operation. @see BackgroundWriteProcess
    '''
        
    thread = BackgroundWriteProcess(fileObj, data, closeWhenFinished, chainAfter)
    thread.start()

    return thread

def bgwrite_chunk(fileObj, data, chunkSize, closeWhenFinished=False, chainAfter=None):
    '''
        bgwrite_chunk - Chunk up the data into even #chunkSize blocks, and then pass it onto #bgwrite.
            Use this to break up a block of data into smaller segments that can be written and flushed.
            The smaller the chunks, the more interactive (recipient gets data quicker, iowait goes down for you) at cost of throughput.

            @see bgwrite

        @param data <string/bytes> - The data to chunk up

        @param chunkSize <integer> - The max siZe of each chunk.
    '''

    chunks = chunk_data(data, chunkSize)

    return bgwrite(fileObj, chunks, closeWhenFinished, chainAfter)
