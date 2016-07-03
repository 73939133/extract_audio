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
- A Python script for HTTP retrieval, in playing order, of the locations and sizes of the data blocks of the first mp3 audio track within a remote mp4 file given, via STDIN, the URL and the location within said file of the location and size tables for said audio track.
- A Python script for HTTP retrieval, to STDOUT, of data blocks of a remote mp4 file given, via STDIN, the URL of the file and the locations and sizes of the blocks.
