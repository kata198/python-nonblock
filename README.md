# python-nonblock
Non-blocking python IO functions


These are pure-python functions which perform non-blocking I/O in python.



**nonblock\_read**

nonblock\_read provides the ability to read anything available on a buffer, like a file or a pipe or a socket, in a non-blocking fashion. Methods like readline will block until a newline is printed, etc.

You can provide a limit (or default None is anything available) and up to that many bytes, if available, will be returned. 

When the stream is closed on the other side, and you have already read all the data (i.e. you've already been returned all data and it's impossible that more will ever be there in the future), "None" is returned.


	def nonblock_read(stream, limit=None, forceMode=None):
		'''
			nonblock_read - Read any data available on the given stream without blocking and regardless of newlines.

				@param stream - A stream (like a file object)
				@param limit <None/int> - Max number of bytes to read. If None or 0, will read as much data is available.
				@param forceMode <None/mode string> - If the stream object doesn't specify a "mode" param (like a socket), this function will assume the encoding as "bytes".
														If you want to force a stream mode, use "t" for text (str), or "b" for binary (bytes). Usually not required.

				@return - Any data available on the stream, or "None" if the stream was closed on the other side and all data has already been read.
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


