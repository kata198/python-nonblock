# python-nonblock
Non-blocking python IO functions


These are pure-python functions which perform non-blocking I/O in python.



**nonblock\_read**

nonblock\_read provides the ability to read anything available on a buffer, like a file or a pipe or a socket, in a non-blocking fashion. Methods like readline will block until a newline is printed, etc.

You can provide a limit (or default None is anything available) and up to that many bytes, if available, will be returned. 

When the stream is closed on the other side, and you have already read all the data (i.e. you've already been returned all data and it's impossible that more will ever be there in the future), "None" is returned.


	def nonblock_read(stream, limit=None, forceMode=None):
		'''
			nonblock_read - Read any data available on the given stream (file, socket, etc) without blocking and regardless of newlines.

				@param stream - A stream (like a file object or a socket)
				@param limit <None/int> - Max number of bytes to read. If None or 0, will read as much data is available.
				@param forceMode <None/mode string> - Default None. Will be autodetected if None. If you want to explicitly force a mode, provide 'b' for binary (bytes) or 't' for text (Str). This determines the return type.

				@return <str or bytes depending on stream's mode> - Any data available on the stream, or "None" if the stream was closed on the other side and all data has already been read.
		'''


Keep in mind that you can only read data that has been flushed from the other side, otherwise it does not exist on the buffer.

If you need to do nonblocking reads on sys.stdin coming from a terminal, you will need to use "tty.setraw(sys.stdin)" to put it in raw mode. See examples/simpleGame.py for an example.


Example usage:


	from nonblock import nonblock_read

	pipe = subprocess.Popen(['someProgram'], stdout=subprocess.PIPE)

	...

	while True:

		data = nonblock_read(pipe.stdout)
		if data is None:
			# All data has been processed and subprocess closed stream
			pipe.wait()
			break
		elif data:
			# Some data has been read, process it
			processData(data)
		else:
			# No data is on buffer, but subprocess has not closed stream
			idleTask()

	# All data has been processed, focus on the idle task
	idleTask()


An example simple game that uses nonblock\_read to drive input whilst always refreshing the map and moving a monster around can be found at: https://github.com/kata198/python-nonblock/blob/master/example/simpleGame.py

**Background Reading - bgread**

Sometimes you may want to collect data from one or more streams in the background, and check/process the data later.

python-nonblock provides this functionality through a method, "bgread". You provide a stream object and options, and it outputs an object which will automatically be populated in the background by a thread, as data becomes available on the stream.


    '''
        bgread - Start a thread which will read from the given stream in a non-blocking fashion, and automatically populate data in the returned object.

            @param stream <object> - A stream on which to read. Socket, file, etc.

            @param blockSizeLimit <None/int> - Number of bytes. Default 65535.

                If None, the stream will be read from until there is no more available data (not closed, but you've read all that's been flushed to straem). This is okay for smaller datasets, but this number effectively controls the amount of CPU time spent in I/O on this stream VS everything else in your application. The default of 65535 bytes is a fair amount of data.

            @param pollTime <float> - Default .03 (30ms) After all available data has been read from the stream, wait this many seconds before checking again for more data.
                
                A low number here means a high priority, i.e. more cycles will be devoted to checking and collecting the background data. Since this is a non-blocking read, this value is the "block", which will return execution context to the remainder of the application. The default of 100ms should be fine in most cases. If it's really idle data collection, you may want to try a value of 1 second.

            @param closeStream <bool> - Default True. If True, the "close" method on the stream object will be called when the other side has closed and all data has been read.



        NOTES --

                blockSizeLimit / pollTime is your effective max-throughput. Real throughput will be lower than this number, as the actual throughput is be defined by:

                T = (blockSizeLimit / pollTime) - DeviceReadTime(blockSizeLimit)

            Using the defaults of .03 and 65535 means you'll read up to 2 MB per second. Keep in mind that the more time spent in I/O means less time spent doing other tasks.


            @return - The return of this function is a BackgroundReadData object. This object contains an attribute "blocks" which is a list of the non-zero-length blocks that were read from the stream. The object also contains a calculated property, "data", which is a string/bytes (depending on stream mode) of all the data currently read. The property "isFinished" will be set to True when the stream has been closed. The property "error" will be set to any exception that occurs during reading which will terminate the thread. @see BackgroundReadData for more info.


    '''


So for example:

	inputData = bgread(sys.stdin)

	processThings()  # Do some stuff that takes some time

	typedData = inputData.data # Get all the input that occured during 'processThings'.



**Background Writing - bgwrite**

python-nonblock provides a clean way to write to streams in a non-blocking, configurable, and interactive-supporting way.

The core of this functionality comes from the bgwrite function:


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

You can create a queue of data to be written to the given stream by using the "chainAfter" param, providing the return of a previous "bgwrite" or "bgwrite\_chunk" function. This will wait for the previous bgwrite to complete before starting the next.

bgwrite will write data in blocks and perform heuristics in order to provide interactivity to other running threads and calculations, based on either a predefined BackgroundIOPriority, or you can provide a custom BackgroundIOPriority (see "Full Documentation" below for the parameters)

*Example*

An example of a script using several bgwrites in addition to performing CPU-bound calculations can be found at: https://github.com/kata198/python-nonblock/blob/master/testWrite.py 


Full Documentation
------------------

Can be found  http://htmlpreview.github.io/?https://github.com/kata198/python-nonblock/blob/master/doc/nonblock.html .


Changes
-------
See: https://raw.githubusercontent.com/kata198/python-nonblock/master/ChangeLog
