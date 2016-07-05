#!/usr/bin/env python
import sys
import httplib
from urlparse import urlparse

def Syntax():
	sys.stderr.write('Please specify http://host/path and offsets to stsc, stsz and stco data boxes\n')
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

if len(sys.argv) < 5:
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

# retrieve stsc chunk header
stscbase = int(sys.argv[2])
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
stszbase = int(sys.argv[3])
buffer = Request(stszbase,20)
tag = ReadTag(buffer,4)
if tag != 'stsz':
	Error('No stsz found')
stszbase += 20	# move to first record
stszsize = ReadUInt32(buffer,16)	# number of block sizes
stszsize *= 4	# 4 bytes per record
stszbase += stszsize	# move to right after the last record
stszblock = ReadUInt32(buffer,12)	# size of global block - 0 if individual sizes
stszfetch = 4 * 1024	# number of bytes to fetch at once - 4 bytes per record

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
stcobase = int(sys.argv[4])
buffer = Request(stcobase,16)
tag = ReadTag(buffer,4)
if tag != 'stco':
	Error('No stco found')
stcobase += 16	# move to first record
chunks = ReadUInt32(buffer,12)	# number of chunks 
stcosize = 4 * chunks	# 4 bytes per record
stcobase += stcosize	# move to right after the last record
stcofetch = 4 * 1024 # number of bytes to fetch at once - 4 bytes per record

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
	# print offset and size
	print str(stco) + '\t' + str(stsc * stsz)
