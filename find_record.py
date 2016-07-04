#!/usr/bin/env python
import sys
import httplib
from urlparse import urlparse

def Syntax():
	sys.stderr.write('Please specify http://host/path and offset to stbl data box\n')
	exit()

def Error(s):
	sys.stderr.write(s+'\n')
	exit()

# returns 32 bit integer at offset n in buffer b
def ReadUInt32(b,n):
	return ord(b[n+3])+(ord(b[n+2])<<8)+(ord(b[n+1])<<16)+(ord(b[n])<<24)

# returns tag at offset n in buffer b
def ReadTag(b,n):
	return b[n:n+4]

if len(sys.argv) < 3:
	Syntax()
url = urlparse(sys.argv[1])
if len(url.scheme) == 0 or len(url.netloc) == 0:
	Syntax()
stblbase = int(sys.argv[2])

# retrieves size bytes at offset from server
def Request(offset,size):
	conn = httplib.HTTPConnection(url.netloc)
	conn.request("GET", url.path, headers={'Range': 'bytes='+str(offset)+'-'+str(offset+size-1)})
	response = conn.getresponse()
	if response.status > 299:
		Error('Error '+httplib.responses[response.status])
	return response.read()

stblsize = stblbase

# retrieve stbl chunk header
buffer = Request(stblbase,8)
tag = ReadTag(buffer,4)
if tag != 'stbl':
	Error('No stbl found')
stblsize += ReadUInt32(buffer,0)
stblbase += 8
stscbase = 0
stszbase = 0
stcobase = 0

while stblbase < stblsize:
	buffer = Request(stblbase,8)
	tag = ReadTag(buffer,4)
	size = ReadUInt32(buffer,0)
	if tag == 'stsc':
		stscbase = stblbase
	if tag == 'stsz':
		stszbase = stblbase
	if tag == 'stco':
		stcobase = stblbase
	stblbase += size

if (stscbase == 0):
	Error('No stsc found')
if (stszbase == 0):
	Error('No stsz found')
if (stcobase == 0):
	Error('No stco found')

print sys.argv[1]
print stscbase
print stszbase
print stcobase
