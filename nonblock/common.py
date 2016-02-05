
__all__ = ('detect_stream_mode', )

def detect_stream_mode(stream):
    '''
        detect_stream_mode - Detect the mode on a given stream

            @param stream <object> - A stream object

            If "mode" is present, that will be used.

        @return <type> - "Bytes" type or "str" type
    '''
    # If "Mode" is present, pull from that
    if hasattr(stream, 'mode'):
        if 'b' in stream.mode:
            return bytes
        elif 't' in stream.mode:
            return str

    # Read a zero-length string off the device 
    if hasattr(stream, 'read'):
        zeroStr = stream.read(0)
        if type(zeroStr) is str:
            return str
        return bytes
    elif hasattr(stream, 'recv'):
        zeroStr = stream.recv(0)
        if type(zeroStr) is str:
            return str
        return bytes

    # Cannot figure it out, assume bytes.
    return bytes
