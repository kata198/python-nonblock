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


An example usage:


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
