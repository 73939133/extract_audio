#!/usr/bin/env python
import sys
import httplib
from urlparse import urlparse

def Syntax():
	sys.stderr.write('Please specify http://host/path\n')
	exit()

def Error(s):
	sys.stderr.write(s+'\n')
	exit()

# return 32 bit integer at offset n in buffer b
def ReadUInt32(b,n):
	return ord(b[n+3])+(ord(b[n+2])<<8)+(ord(b[n+1])<<16)+(ord(b[n])<<24)

#returns tag at offset n in buffer b
def ReadTag(b,n):
	return b[n:n+4]

# looks for subchunk t in buffer b starting at offset n
def SubChunk(b,t,n):
	size = ReadUInt32(buffer,n) # total size of chunk
	n += 8
	while n < size:
		if ReadTag(buffer,n+4) == t:
			return n
		else:
			n += ReadUInt32(buffer,n)

# looks for mp3 ID (105 or 107) in decoder config descriptor within ES descriptor starting in buffer b starting at offset n
def DecodeESDS(b,n):
	if ord(b[n]) != 3:	# check for ES descriptor type tag
		return False
	i = 1
	while (i < 5) and (ord(b[n+i]) > 127):	# up to 3 optional extended tags
		i += 1
	i += 4	# descriptor type length + ES ID + stream priority
	n += i
	if ord(b [n]) != 4:	# check for decoder config descriptor type tag
		return False
	i = 1
	while (i < 5) and (ord(b[n+i]) > 127): # up to 3 optional extended tags
		i += 1
	i += 1	# descriptor type length
	if b [n+i] == 'i':	# 105
		return 105
	if b [n+i] ==  'k':	# 107
		return 107
	return False

# start with some initial setup
if len(sys.argv) < 2:
	Syntax()
url = urlparse(sys.argv[1])
if url.scheme == '' or url.netloc == '':
        Syntax()

# retrieves size bytes at offset from server
def Request(offset,size):
	conn = httplib.HTTPConnection(url.netloc)
	conn.request("GET", url.path, headers={'Range': 'bytes='+str(offset)+'-'+str(offset+size-1)})
	response = conn.getresponse()
	if response.status > 299:
		Error('Error '+httplib.responses[response.status])
	return response.read()

conn = httplib.HTTPConnection(url.netloc)
conn.request("HEAD", url.path)
response = conn.getresponse()
if response.status > 299:
	Error('Error '+httplib.responses[response.status])
filesize = 0
norange = 1
for item in response.getheaders():
	if item[0] == 'content-length':
		filesize = int(item[1])
	if item[0] == 'accept-ranges':
		if item[1] == 'bytes':
			norange = 0

if norange > 0:
	Error('HTTP range not supported')

# retrieve initial header
buffer = Request(0,8)
tag = ReadTag(buffer,4)
if tag != 'ftyp':
	Error('No ftyp found')
size = ReadUInt32(buffer,0)
moovbase = size

# look for moov chunk
while moovbase < filesize:
	buffer = Request(moovbase,8)
	tag = ReadTag(buffer,4)
	size = ReadUInt32(buffer,0)
	if tag == 'moov':
		break
	moovbase += size

if moovbase >= filesize:
	Error('moov tag not found')

# parse moov chunk
moovsize = moovbase+size
moovbase += 8
stblbase = 0
track = 0
while moovbase < moovsize:
	buffer = Request(moovbase,1024)
	tag = ReadTag(buffer,4)
	size = ReadUInt32(buffer,0)
	if tag == 'trak':
		if ReadTag(buffer,12) != 'tkhd':
			Error('Track header missing')
		track = ReadUInt32(buffer,28+8*ord(buffer[16]))
		base = SubChunk(buffer,'mdia',0)
		if base > 0:
			base = SubChunk(buffer,'minf',base)
			if base > 0:
				base = SubChunk(buffer,'stbl',base)
				if base > 0:
					stblbase = moovbase+base
					base = SubChunk(buffer,'stsd',base)
					if base > 0:
						if ReadTag(buffer,base+20) == 'mp4a':
							if ReadTag(buffer,base + 56) == 'esds':
								if DecodeESDS(buffer,base+64):
									break
	moovbase += size

if moovbase < moovsize:
	print sys.argv[1]
	print str(stblbase)
else:
	Error('No mp3 track found')
