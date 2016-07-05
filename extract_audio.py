#!/usr/bin/env python
import sys
import httplib
from urlparse import urlparse
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL)	# this resolves an issue with "IOError: [Errno 32] Broken pipe" when piping the audio stream to mpg321

def Syntax():
	sys.stderr.write('Please specify http://host/path\n')
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

# looks for subchunk t in buffer b starting at offset n
def SubChunk(b,t,n):
	size = ReadUInt32(buffer,n) # total size of chunk
	n += 8
	while n < size:
		if ReadTag(buffer,n+4) == t:
			return n
		else:
			n += ReadUInt32(buffer,n)

# start with some initial setup
if len(sys.argv) < 2:
	Syntax()
url = urlparse(sys.argv[1])
if len(url.scheme) == 0 or len(url.netloc) == 0:
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

if moovbase >= moovsize:
	Error('No mp3 track found')

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

# retrieve stsc chunk header
buffer = Request(stscbase,16)
tag = ReadTag(buffer,4)
if tag != 'stsc':
	Error('No stsc found')
stscbase += 16	# move to second word of first record
stscsize = ReadUInt32(buffer,12) # number of records in stsc data box
stscsize *= 12	# 12 Bytes per record
stscbase += stscsize	# move to right after the last record
stscsize -=  4	# minus one unsigned long to get the number of bytes to fetch
stscfetch = 12 * 1024	# number of bytes to fetch at once - 12 bytes per record

def FetchSTSC():
	global stscsize
	if stscsize < stscfetch:
		buffer = Request(stscbase - stscsize,stscsize)
		buffer += '\xFF\xFF\xFF\xFF'	# append end of file marker
		stscsize = 0
	else:
		buffer = Request(stscbase - stscsize,stscfetch)
		stscsize -= stscfetch
	list = []
	while buffer:
		record = []
		record.append(ReadUInt32(buffer,0))	# number of blocks in chunk
		record.append(ReadUInt32(buffer,8))	# sequence number for next record
		list.append(record)
		buffer = buffer[12:]
	return list

# retrieve stsz chunk header
buffer = Request(stszbase,20)
tag = ReadTag(buffer,4)
if tag != 'stsz':
	Error('No stsz found')
stszbase += 20	# move to first record
stszsize = ReadUInt32(buffer,16)	# number of block sizes
stszsize *= 4	# 4 bytes per record
stszbase += stszsize	# move to right after the last record
stszblock = ReadUInt32(buffer,12)	# size of global block - 0 if individual sizes
stszfetch = 4 * 3072	# number of bytes to fetch at once - 4 bytes per record

def FetchSTSZ():
	global stszsize
	if stszsize < stszfetch:
		buffer = Request(stszbase - stszsize,stszsize)
		stszsize = 0
	else:
		buffer = Request(stszbase - stszsize,stszfetch)
		stszsize -= stszfetch
	list = []
	while buffer:
		list.append(ReadUInt32(buffer,0))
		buffer = buffer[4:]
	return list

if stszblock:
	stszlist = []

# retrieve stco chunk header
buffer = Request(stcobase,16)
tag = ReadTag(buffer,4)
if tag != 'stco':
	Error('No stco found')
stcobase += 16	# move to first record
chunks = ReadUInt32(buffer,12)	# number of chunks
stcosize = 4 * chunks	# 4 bytes per record
stcobase += stcosize	# move to right after the last record
stcofetch = 4 * 3072 # number of bytes to fetch at once - 4 bytes per record

def FetchSTCO():
	global stcosize
	if stcosize < stcofetch:
		buffer = Request(stcobase - stcosize,stcosize)
		stcosize = 0
	else:
		buffer = Request(stcobase - stcosize,stcofetch)
		stcosize -= stcofetch
	list = []
	while buffer:
		list.append(ReadUInt32(buffer,0))
		buffer = buffer[4:]
	return list

# create the lists and initialize
stsclist = stsclist = FetchSTSC()
stsc = stsclist[0][0]	# number of blocks in current chunk
threshold = stsclist[0][1]	# sequence number of next record
stsclist = stsclist[1:]	# remove current item from list
if not stszblock:
	stszlist = []
stcolist = []
sequence = 0	# chunk sequence number

while sequence < chunks:
	sequence += 1
	# retrieve stsc
	if sequence == threshold:
		if not stsclist:
			stsclist = FetchSTSC()
		stsc = stsclist[0][0]	# number of blocks in current chunk
		threshold = stsclist[0][1]	# sequence number of next record
		stsclist = stsclist[1:]	# remove current item from list
	# retrieve stsz
	if not stszblock:	# if individual block sizes are used
		if not stszlist:	# fetch more stsz data if list is empty
			stszlist = FetchSTSZ()	# get the current block size
		stsz = stszlist[0]
		stszlist = stszlist[1:]	# remove current item from list
	else:
		stsz = stszblock# get the global block size
	# retrieve stco
	if not stcolist:	# fetch more stco data if list is empty
		stcolist = FetchSTCO()
	stco = stcolist[0]	# get current chunk offset
	stcolist = stcolist[1:]	# remove current item from list
	# fetch the block
	sys.stdout.write(Request(stco,stsc * stsz))
