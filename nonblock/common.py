
__all__ = ('detect_stream_mode', )

def detect_stream_mode(stream):
    '''
        detect_stream_mode - Detect the mode on a given stream

            @param stream <object> - A stream object

            If "mode" is present, that will be used. 

        @return <str> - 'b' for bytes, 't' for text.
    '''
    # If "Mode" is present, pull from that
    if hasattr(stream, 'mode'):
        if 'b' in stream.mode:
            return 'b'
        elif 't' in stream.mode:
            return 't'

    # Read a zero-length string off the device 
    if hasattr(stream, 'read'):
        zeroStr = stream.read(0)
        if type(zeroStr) is str:
            return 't'
        return 'b'
    elif hasattr(stream, 'recv'):
        zeroStr = stream.recv(0)
        if type(zeroStr) is str:
            return 't'
        return 'b'

    # Cannot figure it out, assume bytes.
    return 'b'
