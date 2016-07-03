program mp4scan;

{$APPTYPE CONSOLE}

uses    SysUtils;

// 32 bit endian swap
function BSWAP (n : cardinal) : cardinal ;
asm
   bswap eax
end ;

procedure makestring (c : array of char ; n : cardinal) ;
asm
   mov   dword ptr [eax],ecx
end ;

var      f           : file ;
         temp        : array [0..1] of cardinal ;
         foffs,fsize : cardinal ;
         chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;

procedure esds (foffs,fsize : cardinal) ;
var      temp        : array [0..17] of byte ;
         i,j         : integer ;
begin
   seek (f,foffs) ;
   blockread (f,temp,18);
   i := 4 ;
   j := i + 4 ;
   if temp [i] = 3 then
   begin
      repeat
         i := i + 1 ;
      until (i > j) or (temp [i] < 128) ;
      i := i + 4 ;
      j := i + 4 ;
      if temp [i] = 4 then
      begin
         repeat
            i := i + 1 ;
         until (i > j) or (temp [i] < 128) ;
         i := i + 1 ;
         writeln ('= esds id    ',temp [i] : 4) ;
      end ;
   end ;
end ;

procedure mp4a (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   seek (f,foffs) ;
   blockread (f,temp,8);
   chunksize := BSWAP (temp [0]) ;
   makestring (chunktype,temp [1]) ;
   writeln ('8 ',chunksize : 10,' ',chunktype) ;
   if chunktype = 'esds' then
      esds (foffs + 8,foffs + chunksize) ;
end ;

procedure stsd (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   seek (f,foffs) ;
   blockread (f,temp,8);
   chunksize := BSWAP (temp [0]) ;
   makestring (chunktype,temp [1]) ;
   writeln ('7 ',chunksize : 10,' ',chunktype) ;
   if chunktype = 'mp4a' then
      mp4a (foffs + 36,foffs + chunksize) ;
end ;

procedure stbl (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   while foffs < fsize do
   begin
      seek (f,foffs) ;
      blockread (f,temp,8);
      chunksize := BSWAP (temp [0]) ;
      makestring (chunktype,temp [1]) ;
      writeln ('6 ',chunksize : 10,' ',chunktype) ;
      if chunktype = 'stsd' then
         stsd (foffs + 16,foffs + chunksize) ;
{
      if chunktype = 'stsc' then
         stsc (foffs + 8,foffs + chunksize) ;
      if chunktype = 'stsz' then
         stsz (foffs + 8,foffs + chunksize) ;
      if chunktype = 'stco' then
         stco (foffs + 8,foffs + chunksize) ;
}
      foffs := foffs + chunksize ;
   end ;
end ;

procedure minf (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   while foffs < fsize do
   begin
      seek (f,foffs) ;
      blockread (f,temp,8);
      chunksize := BSWAP (temp [0]) ;
      makestring (chunktype,temp [1]) ;
      writeln ('5 ',chunksize : 10,' ',chunktype) ;
      if chunktype = 'stbl' then
         stbl (foffs + 8,foffs + chunksize) ;
      foffs := foffs + chunksize ;
   end ;
end ;

procedure hdlr (foffs,fsize : cardinal) ;
var      chunktype   : array [0..3] of char ;
         temp        : array [0..2] of cardinal ;
begin
   seek (f,foffs) ;
   blockread (f,temp,12);
   makestring (chunktype,temp [2]) ;
   writeln ('= hdlr type  ',chunktype) ;
end ;

procedure mdia (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   while foffs < fsize do
   begin
      seek (f,foffs) ;
      blockread (f,temp,8);
      chunksize := BSWAP (temp [0]) ;
      makestring (chunktype,temp [1]) ;
      writeln ('3 ',chunksize : 10,' ',chunktype) ;
      if chunktype = 'hdlr' then
         hdlr (foffs + 8,foffs + chunksize) ;
      if chunktype = 'minf' then
         minf (foffs + 8,foffs + chunksize) ;
      foffs := foffs + chunksize ;
   end ;
end ;

procedure tkhd (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         temp        : array [0..3] of cardinal ;
begin
   seek (f,foffs) ;
   blockread (f,temp,16);
   chunksize := BSWAP (temp [3]) ;
   writeln ('= tkhd id    ',chunksize : 4) ;
end ;

procedure trak (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   while foffs < fsize do
   begin
      seek (f,foffs) ;
      blockread (f,temp,8);
      chunksize := BSWAP (temp [0]) ;
      makestring (chunktype,temp [1]) ;
      writeln ('2 ',chunksize : 10,' ',chunktype) ;
      if chunktype = 'tkhd' then
         tkhd (foffs + 8,foffs + chunksize) ;
      if chunktype = 'mdia' then
         mdia (foffs + 8,foffs + chunksize) ;
      foffs := foffs + chunksize ;
   end ;
end ;

procedure moov (foffs,fsize : cardinal) ;
var      chunksize   : cardinal ;
         chunktype   : array [0..3] of char ;
         temp        : array [0..1] of cardinal ;
begin
   while foffs < fsize do
   begin
      seek (f,foffs) ;
      blockread (f,temp,8);
      chunksize := BSWAP (temp [0]) ;
      makestring (chunktype,temp [1]) ;
      writeln ('1 ',chunksize : 10,' ',chunktype) ;
      if chunktype = 'trak' then
         trak (foffs + 8,foffs + chunksize) ;
      foffs := foffs + chunksize ;
   end ;
end ;

begin
   if paramcount = 0 then
      halt (1) ;
   foffs := 0 ;
   assignfile (f,paramstr (1)) ;
   reset (f,1) ;
   fsize := filesize (f) ;
   while foffs < fsize do
   begin
      seek (f,foffs) ;
      blockread (f,temp,8);
      chunksize := BSWAP (temp [0]) ;
      makestring (chunktype,temp [1]) ;
      writeln ('0 ',chunksize : 10,' ',chunktype) ;
      if chunktype = 'moov' then
         moov (foffs + 8,foffs + chunksize) ;
      foffs := foffs + chunksize ;
   end ;
   closefile (f) ;
end.
