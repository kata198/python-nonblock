'''
    Copyright (c) 2015-2016 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    read.py Contains pure-python functions for non-blocking reads in python

	
'''
# vim: ts=4 sw=4 expandtab
import sys
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

    # See if this is a buffered stream which supports the "getbuffn" call.
    #    getbuffn is a yet-to-be-submitted/accepted additional call in the
    #     python api for a BufferedReader stream.
    #
    # It returns the number of bytes which are waiting to be returned in the
    #   underlying stream buffer.
    #
    # On a typical linux filesystem which uses 4096 byte I/O blocks, the "read"
    #  call will end up reading 4096 bytes, yet we read just 1,
    #   in order to prevent blocking (by selecting each byte).
    #
    #  This means that for a filesystem non-blocking I/O read, we are basically
    #    adding the unnecessary overhead of a select syscall, a call to the python read,
    #    and all the associated overhead of those functions and going from C-mode to Py-mode
    #   4095 times out of 4096.
    #
    #  Also helps a lot with scheduling on a loaded system as we are limiting the amount of
    #   times we allow ourselves to be pre-empted
    #
    #  With the addition of "getbuffn" we are able to suck up that full buffer in one swing.
    #
    #   On a 5 meg file from a VM which is running on an SSD, I average the following:
    #
    #    Loaded system, non-cached I/O:
    #
    #       One-Fell-Swoop file.read() - .3 seconds
    #
    #       getbuffn-patched python and this impl - 3.1 seconds
    #
    #       unpatched python and this impl - 41 to 55 = 44 seconds. ( avg min - avg max)
    #
    #    Unloaded system, cached I/O:
    #
    #       One-Fell-Swoop file.read() - .0017 seconds
    #
    #       getbuffn-patched python and this impl - .034 seconds
    #
    #       unpatched python and this impl - 45 seconds. ( not as variable as loaded system )
    #
    #
    #  TODO:
    #       - This call has been "hacked-in" with the existing function-flow
    #          for ease of analysis and comparison. In reality, we should be
    #          calling getbuffn AFTER we read the single byte, which will
    #          save a loop iteration and a call to select
    #
    #       - Currently we ignore the #limit parameter and may over-read with
    #          this impl. We should thus choose to read the minimum of
    #          available bytes (getbuffn ret) and (limit - bytesRead)

    #if True:
    #    hasGetBuffN = False   
    #elif hasattr(stream, 'getbuffn'):
    if hasattr(stream, 'getbuffn'):
        print ( "getbuffn detected (direct)" )
        hasGetBuffN = True
        getbuffn = stream.getbuffn
    elif hasattr(stream, 'buffer') and hasattr(stream.buffer, 'getbuffn'):
        print ( "getbuffn detected (on .buffer obj)" )
        hasGetBuffN = True
        getbuffn = stream.buffer.getbuffn
    else:
        print ( "No 3 ")
        hasGetBuffN = False

    while True:
        # Check if data on stream is immediately available
        (readyToRead, junk1, junk2) = select.select([stream], [], [], .000001)

        if not readyToRead:
            break

        numToRead = 1

        if hasGetBuffN:
            availableBytes = getbuffn()

            if availableBytes > 0:
                #sys.stderr.write('Got %d buffered bytes!\n' %(availableBytes, ))
                #sys.stderr.flush()
                numToRead = availableBytes
                

        if numToRead == 1:
            c = readByte()
        else:
            # TODO: Should we be calling "read" or "read1" here?
            #         "read1" seems to make the most sense conceptually,
            #         but based on readahead maybe "read" could be better?
            #
            #         "read" does seem to test slightly better than read1
            #            on an SSD
            c = stream.read(numToRead)
            #c = stream.read1(numToRead)

        if c == emptyStr:
            # Stream has been closed
            if not ret:
                # All data already read, so return None
                return None
            # Otherwise, return data collected. Next call will return None.
            break

        bytesRead += numToRead
        ret.append(c)

        if limit and bytesRead >= limit:
            break

    return emptyStr.join(ret)


