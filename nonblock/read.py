'''
    Copyright (c) 2015-2016 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    read.py Contains pure-python functions for non-blocking reads in python

	
'''
# vim: ts=4 sw=4 expandtab

import select

from .common import detect_stream_mode

__all__ = ('nonblock_read', )

def nonblock_read(stream, limit=None, forceMode=None):
    '''
        nonblock_read - Read any data available on the given stream (file, socket, etc) without blocking and regardless of newlines.

            @param stream <object> - A stream (like a file object or a socket)
            @param limit <None/int> - Max number of bytes to read. If None or 0, will read as much data is available.
            @param forceMode <None/mode string> - Default None. Will be autodetected if None. If you want to explicitly force a mode, provide 'b' for binary (bytes) or 't' for text (Str). This determines the return type.

            @return <str or bytes depending on stream's mode> - Any data available on the stream, or "None" if the stream was closed on the other side and all data has already been read.
    '''
    bytesRead = 0
    ret = []

    if forceMode:
        if 'b' in forceMode:
            streamMode = bytes
        elif 't' in forceMode:
            streamMode = str
        else:
            streamMode = detect_stream_mode(stream)
    else:
        streamMode = detect_stream_mode(stream)

    emptyStr = streamMode()

    # Determine if our function is "read" (file-like objects) or "recv" (socket-like objects)
    if hasattr(stream, 'read'):
        readByte = lambda : stream.read(1)
    elif hasattr(stream, 'recv'):
        readByte = lambda : stream.recv(1)
    else:
        raise ValueError('Cannot determine how to read from provided stream, %s.' %(repr(stream),))

    while True:
        # Check if data on stream is immediately available
        (readyToRead, junk1, junk2) = select.select([stream], [], [], .000001)

        if not readyToRead:
            break

        c = readByte()
        if c == emptyStr:
            # Stream has been closed
            if not ret:
                # All data already read, so return None
                return None
            # Otherwise, return data collected. Next call will return None.
            break

        bytesRead += 1
        ret.append(c)

        if limit and bytesRead >= limit:
            break

    return emptyStr.join(ret)


