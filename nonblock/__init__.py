'''
    Copyright (c) 2015-2016 Timothy Savannah under terms of LGPLv2. You should have received a copy of this LICENSE with this distribution.

    Contains pure-python functions for non-blocking IO in python
'''
# vim: ts=4 sw=4 expandtab


from .read import nonblock_read

from .BackgroundWrite import bgwrite, bgwrite_chunk, BackgroundIOPriority

from .BackgroundRead import bgread

__all__ = ('nonblock_read', 'bgwrite', 'bgwrite_chunk', 'BackgroundIOPriority', 'bgread')

__version__ = '3.0.1'
__version_tuple = (3, 0, 1)

