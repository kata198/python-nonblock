'''
    Copyright (c) 2015-2016 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    read.py Contains pure-python functions for non-blocking reads in python

	
'''
# vim: ts=4 sw=4 expandtab

import time
import threading

from .read import nonblock_read

from .common import detect_stream_mode

__all__ = ('BackgroundReadData', 'background_read' )

def background_read(stream, blockSizeLimit=65535, pollTime=.03):
    '''
        background_read - Start a thread which will read from the given stream in a non-blocking fashion, and automatically populate data in the returned object.

            @param stream <object> - A stream on which to read. Socket, file, etc.

            @param blockSizeLimit <None/int> - Number of bytes. Default 65535.

                If None, the stream will be read from until there is no more available data (not closed, but you've read all that's been flushed to straem). This is okay for smaller datasets, but this number effectively controls the amount of CPU time spent in I/O on this stream VS everything else in your application. The default of 65535 bytes is a fair amount of data.

            @param pollTime <float> - Default .03 (30ms) After all available data has been read from the stream, wait this many seconds before checking again for more data.
                
                A low number here means a high priority, i.e. more cycles will be devoted to checking and collecting the background data. Since this is a non-blocking read, this value is the "block", which will return execution context to the remainder of the application. The default of 100ms should be fine in most cases. If it's really idle data collection, you may want to try a value of 1 second.



        NOTES --

                blockSizeLimit / pollTime is your effective max-throughput. Real throughput will be lower than this number, as the actual throughput is be defined by:

                T = (blockSizeLimit / pollTime) - DeviceReadTime(blockSizeLimit)

            Using the defaults of .03 and 65535 means you'll read up to 2 MB per second. Keep in mind that the more time spent in I/O means less time spent doing other tasks.


            @return - The return of this function is a BackgroundReadData object. This object contains an attribute "blocks" which is a list of the non-zero-length blocks that were read from the stream. The object also contains a calculated property, "data", which is a string/bytes (depending on stream mode) of all the data currently read. The property "isFinished" will be set to True when the stream has been closed. The property "error" will be set to any exception that occurs during reading which will terminate the thread. @see BackgroundReadData for more info.


    '''
    try:
        pollTime = float(pollTime)
    except ValueError:
        raise ValueError('Provided poll time must be a float.')
    if blockSizeLimit is not None:
        try:
            blockSizeLimit = int(blockSizeLimit)
            if blockSizeLimit <= 0:
                raise ValueError()
        except ValueError:
            raise ValueError('Provided block size limit must be "None" for no limit, or a positive integer.')

    streamMode = detect_stream_mode(stream)
    results = BackgroundReadData(streamMode)

    thread = threading.Thread(target=_do_background_read, args=(stream, blockSizeLimit, pollTime, results))
    thread.daemon = True # Automatically terminate this thread if program closes
    thread.start()

    return results

class BackgroundReadData(object):
    '''

        BackgroundReadData - An object returned by the background_read function. This object is automatically populated in the background by a thread with data read off the stream.

        It contains the following attributes:

            blocks - The raw non-zero length blocks read from the stream, in order.

            data - A calculated property, which is a bytes/str (depending on stream mode). It is the joining of all the read blocks, and contains all the data read to-date.

            isFinished - starts False, and becomes True after all data has been read from the stream. Will remain False if there is an exception raised during I/O
            
            error - starts None, and is set to any exception that is raised during reading (which will also terminate the thread)
    '''

    def __init__(self, dataType):
        self.blocks = []
        self.dataType = dataType
        self.emptyStr = dataType()

        self.isFinished = False
        self.error = None

    def addBlock(self, block):
        self.blocks.append(block)

    @property
    def data(self):
        '''
            data - property to get the data as a string or bytes.
                Use "blocks" to access the individual blocks of data

            @return <str or bytes> - All data currently read, as a string or bytes (depending on the dataType)
        '''

        return self.emptyStr.join(self.blocks)
        



def _do_background_read(stream, blockSizeLimit, pollTime, results):
    '''
        _do_background_read - Worker functon for the background read thread.

        @param stream <object> - Stream to read until closed
        @param results <BackgroundReadData>
    '''

    # Put the whole function in a try instead of just the read portion for performance reasons.
    try:
        while True:
            nextData = nonblock_read(stream, limit=blockSizeLimit)
            if nextData is None:
                break
            elif nextData:
                results.addBlock(nextData)

            time.sleep(pollTime)
    except Exception as e:
        results.error = e
        return

    results.isFinished = True
