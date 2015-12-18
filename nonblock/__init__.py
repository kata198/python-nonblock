'''
    Copyright (c) 2015 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    Contains pure-python functions for non-blocking IO in python
'''
# vim: ts=4 sw=4 expandtab

import select
import sys

__all__ = ('nonblock_read', )

__version__ = '1.0.0'
__version_tuple = (1, 0, 0)

def nonblock_read(stream, limit=None, forceMode=None):
    '''
        nonblock_read - Read any data available on the given stream without blocking and regardless of newlines.

            @param stream - A stream (like a file object)
            @param limit <None/int> - Max number of bytes to read. If None or 0, will read as much data is available.
            @param forceMode <None/mode string> - If the stream object doesn't specify a "mode" param (like a socket), this function will assume the encoding as "bytes".
                                                    If you want to force a stream mode, use "t" for text (str), or "b" for binary (bytes). Usually not required.

            @return - Any data available on the stream, or "None" if the stream was closed on the other side and all data has already been read.
    '''
    bytesRead = 0
    ret = []

    if not forceMode:
        # If "Mode" is present, require 'b' for bytes mode.
        if hasattr(stream, 'mode'):
            if 'b' in stream.mode:
                emptyStr = b''
            else:
                emptyStr = ''
        else:
            # No "mode" param, and no provided mode, so assume bytes
            emptyStr = b''
    else:
        # Provided mode, if they provided "b", 
        if 'b' in forceMode:
            emptyStr = b''
        else:
            emptyStr = ''
                
    while True:
        # Check if data on stream is immediatly available
        (readyToRead, junk1, junk2) = select.select([stream], [], [], .000001)
        if not readyToRead:
            break

        c = stream.read(1)
        if c == emptyStr:
            # Stream has been closed
            if not ret:
                return None
            break

        bytesRead += 1
        ret.append(c)

        if limit and bytesRead >= limit:
            break

    return emptyStr.join(ret)

