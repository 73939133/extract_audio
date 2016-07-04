# extract_audio
Command line utility to extract mp3 audio from mp4 retrieved via http

The task is to write a program or script that extracts the first mp3 audio track from a remote mp4 file over HTTP and pipes it to stdout.
Any basic mp3 player should be able to play the track using the remote content without downloading the entire file.

In order to consider the task completed, the following features should be implemented:
- Playback should start almost immediately without downloading the whole file first.
- The program should work with any mp4 source containing mp3 tracks.
- The program should include mp4 parsing code that does not depend on already made implementations such as libavformat.

The file mp4-layout.txt contains the mp4 file format specification used.

En route to completion there will be several programs or scripts written:
- A Delphi console application for pinpointing the positions of certain chunks within mp4 files in order to verify my understanding of the mp4 file format and the validity of the parsing scheme used.
- A Python script for HTTP retrieval, to STDOUT,  of the information needed to properly identify (if any) the first mp3 audio track in a remote mp4 file and to report the location within said mp4 file of the tables specifying the locations and sizes of all data blocks in said audio track.
- A Python script for HTTP retrieval, to STDOUT, in playing order, of the locations and sizes of the data blocks of the first mp3 audio track within a remote mp4 file given, via STDIN, the URL and the location within said file of the location and size tables for said audio track.
- A Python script for HTTP retrieval, to STDOUT, of data blocks of a remote mp4 file given, via STDIN, the URL of the file and the locations and sizes of the blocks.

Constraints:
This is just an exercise and I have chosen to not support files larger than 4 GiB, mostly because of the bandwidth needed to retrieve files for testing.
Because this exercise specification requires playback to begin without downloadint the entire file, HTTP servers without support for byte ranges are not supported. 

The solution:
The mp4 file format contains a number of data boxes. The format varies between them, but they all start with a 32-bit offset and 4 bytes ASCII type string.
The offset indicates the offset from the beginning of the offset field to the next box and indicates the total size of the current box, including the offset and type fields.
The rest of the box is the actual payload of the box and can contain other boxes. If, how many and what types depend on the type of box and can be found in the mp4 file format specification.
Parsing the file boils down to reading 8 bytes (offset and type) and either processing the box (if it's a box containing useful information) or using the offset to find the location of the next box, until end of file.
The mdat box can be rather large and isn't required to be located after the moov box, making it impossible to successfully complete this exercise without byte range support from the HTTP server, hence the constraint specified above.

On the root level there are several types of boxes but the only ones needed, except for the initial sanity check that the file starts with a box of type ftyp, are the moov and mdat boxes.
Of those two, the former contains all the data needed to locate the data blocks needed for track retrieval and the latter contains the data blocks. The latter, however, won't be read directly, as the offsets to each data block specified in the moov box refers to the beginning of the file and not of the mdat box.

In the moov box, there are several boxes of which only the trak boxes are needed.
Each trak box is parsed for the necessary information only.
Thus, the tkhd box is skipped because the tarck ID isn't relevant, as the task is to retrieve the first audio track containing mp3 audio, not a track with a specified track number.
The mdia box is parsed, but the mdhd box is skipped, even though its hdlr box contains the tag soun if this is an audio track, because wether this is an mp3 track or not is specified in the minf box.
The minf box is then parsed to locate the stbl box. The offset of this box is saved at this point, in case this track is identified as the correct one.
In the stbl box, the stsd box is located and parsed. If the audio format description is not mp4a, then the parsing continues with the next trak box.
If the tag mp4a is found, then parsing of the stsd box continues in order to locate the esds, in which object type ID is retrieved and either MPEG-2 ADTS (code 105) or MPEG-1 ADTS (code 107) is accepted and the saved stbl offset is processed further. Anything else will return to the parsing of the next trak box.
If no tracks are found containing mp3 audio, the script is terminated with an error message.

The next step is to retrieve the relevant audio track.
Using the offset of the stbl box provided by the parsing is now used to parse the stbl box for three boxes:
stsc - contains a list of serial numbers and chunk sizes. The serial number is that of the first audio chunk to use this chunk and the chunk size is the number of block in this chunk. The first record contains the chunk size for audio chunk 1 and only serial numbers for chunks that differ in size from the previous ones are specified.
stsz - contains the standard block size and, if that size is 0, a list of block sizes.
stco - contains a list of offsets within the file of each chunk in this track.

The offsets (from stco) and the sizes in bytes, calculated by multiplying the block size (from stsz) by the chunk size (from stsc), can now be fed into the block retriever.
All that is left for the block retriever to do is to request the blocks at said offset with said size.

More to follow...
