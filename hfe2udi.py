# hfe2udi.py
#
# HFEv1 to UDIv1 to HFEv1 converter
#
# Written by Denis Dratov aka Dexus <volutar@gmail.com>
#
# This is free and unencumbered software released into the public domain.
# See the file COPYING for more details, or visit <http://unlicense.org>.

import sys, struct, argparse, time, os
from demfm import DeMFM

tracks_mfm=[]
tracks=[]
syncs=[]
sectors=[]
cyls=0
sides=0
_CRC=0xffffffff

def udicrc(buf):
  global _CRC
  for i in range(len(buf)):
    _CRC ^= 0xffffffff ^ buf[i]
    for k in range(8):
      temp=_CRC&1
      _CRC=(_CRC&0x80000000)|_CRC>>1
      if temp: _CRC^=0xedb88320
    _CRC ^= 0xffffffff
    if i&0x7fff==0:
      print('.',end='')
      sys.stdout.flush()
  return _CRC

#mirrored version, special for hfe
def domfm(code,prev=0,sync=False):
  res=0
  for i in range(8):
    cur = (code) & 0x80
    res>>=1
    if (prev == cur):
      res += (0x80-prev)<<8
    res>>=1
    res += cur<<8
    prev=cur;
    code<<=1
  if sync:
    if res==0x9522: res=0x9122
    elif res==0x254a: res=0x244a
  return (res,prev)
  #2a49=4e #9122=a1` #9522=a1 #244a=c2` #254a=c2
mfmtab=[0x5555,0x9555,0x2555,0xA555,0x4955,0x8955,0x2955,0xA955,
0x5255,0x9255,0x2255,0xA255,0x4A55,0x8A55,0x2A55,0xAA55,
0x5495,0x9495,0x2495,0xA495,0x4895,0x8895,0x2895,0xA895,
0x5295,0x9295,0x2295,0xA295,0x4A95,0x8A95,0x2A95,0xAA95,
0x5525,0x9525,0x2525,0xA525,0x4925,0x8925,0x2925,0xA925,
0x5225,0x9225,0x2225,0xA225,0x4A25,0x8A25,0x2A25,0xAA25,
0x54A5,0x94A5,0x24A5,0xA4A5,0x48A5,0x88A5,0x28A5,0xA8A5,
0x52A5,0x92A5,0x22A5,0xA2A5,0x4AA5,0x8AA5,0x2AA5,0xAAA5,
0x5549,0x9549,0x2549,0xA549,0x4949,0x8949,0x2949,0xA949,
0x5249,0x9249,0x2249,0xA249,0x4A49,0x8A49,0x2A49,0xAA49,
0x5489,0x9489,0x2489,0xA489,0x4889,0x8889,0x2889,0xA889,
0x5289,0x9289,0x2289,0xA289,0x4A89,0x8A89,0x2A89,0xAA89,
0x5529,0x9529,0x2529,0xA529,0x4929,0x8929,0x2929,0xA929,
0x5229,0x9229,0x2229,0xA229,0x4A29,0x8A29,0x2A29,0xAA29,
0x54A9,0x94A9,0x24A9,0xA4A9,0x48A9,0x88A9,0x28A9,0xA8A9,
0x52A9,0x92A9,0x22A9,0xA2A9,0x4AA9,0x8AA9,0x2AA9,0xAAA9,
0x5552,0x9552,0x2552,0xA552,0x4952,0x8952,0x2952,0xA952,
0x5252,0x9252,0x2252,0xA252,0x4A52,0x8A52,0x2A52,0xAA52,
0x5492,0x9492,0x2492,0xA492,0x4892,0x8892,0x2892,0xA892,
0x5292,0x9292,0x2292,0xA292,0x4A92,0x8A92,0x2A92,0xAA92,
0x5522,0x9522,0x2522,0xA522,0x4922,0x8922,0x2922,0xA922,
0x5222,0x9222,0x2222,0xA222,0x4A22,0x8A22,0x2A22,0xAA22,
0x54A2,0x94A2,0x24A2,0xA4A2,0x48A2,0x88A2,0x28A2,0xA8A2,
0x52A2,0x92A2,0x22A2,0xA2A2,0x4AA2,0x8AA2,0x2AA2,0xAAA2,
0x554A,0x954A,0x254A,0xA54A,0x494A,0x894A,0x294A,0xA94A,
0x524A,0x924A,0x224A,0xA24A,0x4A4A,0x8A4A,0x2A4A,0xAA4A,
0x548A,0x948A,0x248A,0xA48A,0x488A,0x888A,0x288A,0xA88A,
0x528A,0x928A,0x228A,0xA28A,0x4A8A,0x8A8A,0x2A8A,0xAA8A,
0x552A,0x952A,0x252A,0xA52A,0x492A,0x892A,0x292A,0xA92A,
0x522A,0x922A,0x222A,0xA22A,0x4A2A,0x8A2A,0x2A2A,0xAA2A,
0x54AA,0x94AA,0x24AA,0xA4AA,0x48AA,0x88AA,0x28AA,0xA8AA,
0x52AA,0x92AA,0x22AA,0xA2AA,0x4AAA,0x8AAA,0x2AAA,0xAAAA]

def domfm2(code,prev=0,sync=False):
  res=mfmtab[code]
  if prev==0x8000: res=res&0xfffe
  if sync:
    if res==0x9522: res=0x9122
    elif res==0x254a: res=0x244a
  return (res,res&0x8000) 


def remove_unformatted():
  global tracks_mfm, tracks, syncs, sectors, cyls, sides
  return
  if len(tracks)>160:
    deleted=0
    for tr in range(len(tracks)-1,159,-1):
      ok=False
      for i in range(len(sectors[tr])):
        if sectors[tr][i][1]>=0xf8 or sectors[tr][i][1]==1 or sectors[tr][i][1]==2:
          ok=True
          break
      if not ok:
        print("Removing unformatted track:",tr)
        deleted+=1
        tracks.pop(tr)
        syncs.pop(tr)
        sectors.pop(tr)
    cyls-=deleted//2
    if deleted%2==1:
      print("Returning uneven empty track")
      tracks.append(bytearray([]))
      syncs.append(bytearray([]))
      sectors.append([])


#################################################################
def importudi(filename,recover=False,preserve=False):
  global tracks_mfm, tracks, syncs, sectors, cyls, sides, _CRC
  with open(filename, "rb") as f:
    dat = f.read()

  header = struct.unpack("<4sI4BI",dat[0:16])

  if header[0] != b"UDI!":
    print ("Not UDIv1 format")
    return False
  length = header[1]
  if header[2] != 0:
    print ("Wrong UDI version")
    return False
  cyls = header[3]+1
  sides = header[4]+1
  if header[6] != 0:
    print ("EXTHDL size is not 0 (probably wrong format)")
    return False
  print ("Importing UDIv1 file \"%s\"..." %filename)
  print ("Cyls:", cyls," Sides:", sides)

  if cyls>128:
    print ("Too many cylinders")
    return False

  cur_off = 16
  track_num = sides*cyls

  curtime=time.time()
  tracks=[]
  syncs=[]
  sectors=[]
  tracks_mfm=[]
  demfm=DeMFM()

  tlen=0
  clen=0
  for c in range(track_num):
#  for c in range(2):
#  for c in range(4):
    trk=struct.unpack("<BH",dat[cur_off:cur_off+3])
    tlen=trk[1]
    clen=tlen // 8 + (tlen % 8 + 7) // 8
#    print("track",c,"offset",cur_off,"tlen",tlen,"clen",clen)
#    print ("off=%08X"%cur_off,end=' ')
    print ("%d"%(tlen),end=' ')
    cur_off+=3

    tracks.append(dat[cur_off : cur_off + tlen])
    syncs.append(dat[cur_off + tlen : cur_off + tlen + clen])
    #there is no catalog parsing for UDI data
    cur_off += tlen + clen
#    for x in range(len(syncs[c])):
#      print ("%02X "%syncs[c][x],end='')
#    print()
    
    d = 0
    trk_dat=bytearray()
    for x in range(len(tracks[c])):
      sn=syncs[c][x//8]>>(x%8)&1
      (bt,d)=domfm2(tracks[c][x],d,sn==1)
      trk_dat.append(bt&0xff)
      trk_dat.append((bt>>8)&0xff)
#      if x%8==0: print ("\n=%02X "%syncs[c][x//8],end='')
#      print ("%02X"%tracks[c][x],end='')
#      if sn==1: print(".",end='')
#      print(' ',end='')
    tracks_mfm.append(trk_dat)
    demfm.decode_mfm(trk_dat,recover=recover,preserve=preserve)
    if recover:  #### another try, with recovered A1 -- so it goes a bit longer
      tracks_mfm.pop()
      tracks.pop()
      syncs.pop()
      d = 0
      trk_dat=bytearray()
      for x in range(len(demfm.bytes)):
        sn=demfm.syncs[x//8]>>(x%8)&1
        (bt,d)=domfm2(demfm.bytes[x],d,sn==1)
        trk_dat.append(bt&0xff)
        trk_dat.append((bt>>8)&0xff)
      tracks_mfm.append(trk_dat)
      tracks.append(demfm.bytes)
      syncs.append(demfm.syncs)

    sectors.append(demfm.cat)
    print("%03d: "%c,end="") 
    demfm.print_cat_short()

    for x in range(0,len(demfm.bytes)):
      print(" {:02X}".format(demfm.bytes[x]),end="")
      if (demfm.syncs[x//8]>>(x%8))&1: print(".",end="")
    print("\n")

#  print(len(dat),cur_off)
  
  crcsize=len(dat[cur_off:cur_off+4])
  if crcsize!=4:
    crc[0]=-1
    print("CRC is misplaced")
  else:
    (crc)=struct.unpack("<I",dat[cur_off:cur_off+4])
    print ("CRC = 0x%08X"%crc)
  
  print("Import time:",time.time()-curtime)

  remove_unformatted()
  '''
  if crc[0]!=-1:
    _CRC=0xffffffff
    print("Calculating CRC:",end="")
    udicrc(dat[0:-4])
    print()
    if crc[0]==_CRC:
      print("CRC check Ok (0x%04X)" %_CRC)
    else:
      print("Wrong CRC! (file=0x%04X, calc=0x%04X)" %(crc[0],_CRC))
  '''

#################################################################
def importhfe(filename,preserve=False):
  global tracks_mfm, tracks, syncs, sectors, cyls, sides, _CRC
  with open(filename, "rb") as f:
    dat = f.read()

  header = struct.unpack("<8s4B2H2B1H", dat[0:20])
  if header[0] != b"HXCPICFE":
    print ("Not HFEv1 format")
    return False
  cyls = dat[9]
  sides = dat[10]
  tlut = header[9]
  print ("Importing HFEv1 file \"%s\"..." %filename)
  print ("Cyls:", cyls," Sides:", sides)
  if cyls>128:
    print ("Too many cylinders")
    return False
  unps="<"+str(cyls*2)+"H"
  trk_offs = struct.unpack(unps, dat[0x200*tlut:0x200*tlut+cyls*4])
#  print (trk_offs)

  track_range = range(cyls)

  demfm=DeMFM()
  diag=False

  curtime=time.time()
  tracks_mfm=[]
  tracks=[]
  syncs=[]
  sectors=[]

#  for tr in range (4):
#  for tr in range (80,81):
  for tr in track_range:
    trk_start = trk_offs[tr*2] * 512
    trk_size = trk_offs[tr*2+1]
#    print (tr,': ',trk_start,' ',trk_size,end=" ")
    print (trk_size//4,end=' ') ########

    trk_dat1=bytearray()
    trk_dat2=bytearray()
    j=-256
#    print ('trksize=',trk_size)
    for i in range (trk_size//2): #reassemble hfe interleaved data
      if i%256==0: j+=256
#      if i>12300: print (i,j,256,end=', ')
      trk_dat1.append(dat[trk_start+i+j]) #side 0
      trk_dat2.append(dat[trk_start+256+i+j]) #side 1
#    print(trk_start,i,j)
#    print (trk_dat1)  
#    print(" ==== SIDE A")
    tracks_mfm.append(trk_dat1)
    demfm.decode_mfm(trk_dat1,preserve=preserve)
    print("%03d: "%(tr*2),end="") 
#    demfm.print_cat()
#    for idx in range(0xfff):
#      if idx>=0xc80 and idx<=0xd80:
#        print("%02X"%(demfm.bytes[idx]),end=' ')

    tracks.append(demfm.bytes)
    syncs.append(demfm.syncs)
    sectors.append(demfm.cat)
#    print(tracks[tr*2])
    if not diag:
      if len(demfm.cat)>0:
        if len(demfm.cat[0])>0:
          if demfm.cat[0][1]==1:
            print("Amiga disk format")
#    demfm.print_cat()

    demfm.print_cat_short()
    diag=True;

#    print(" ==== SIDE B")
    if sides==2:
      print (trk_size//4,end=' ') ########
      demfm.decode_mfm(trk_dat2,preserve=preserve)
      tracks_mfm.append(trk_dat2)
      print("%03d: "%(tr*2+1),end="") 
      tracks.append(demfm.bytes)
      syncs.append(demfm.syncs)
      sectors.append(demfm.cat)
#    print(tracks[tr*2+1])
#    demfm.print_cat()
      demfm.print_cat_short()
  print("Import time:",time.time()-curtime)

  remove_unformatted()
#  print(length(sectors))


#################################################################
def exporthfe(filename):
  global tracks_mfm, tracks, syncs, sectors, cyls, sides, _CRC

  print ()
  print ("Exporting HFE file v1.0 \"%s\"..." %filename)

  #    if len(sectors[tr])!=32: print(sectors[tr])
  #    print('.',end='')
  #  print(length)
  header = struct.pack("<8s4B2H2BH2B",
    b"HXCPICFE",#  0 Signature
    0,          #  8 Revision
    cyls,       #  9 Cylinders
    sides,      # 10 Number of sides
    0,          # 11 Track encoding: 0=ibm mfm, 1=amiga mfm, 2=ibm fm, 3=emu fm
    250,        # 12 Bitate in kb/s
    0,          # 14 RPM
    255,        # 16 Interface mode: 0=ibm dd, 1=ibm hd, 2=atari dd, 3=atari hd,
                # 4=amiga dd, 5=amiga hd, 6=cpc dd, 7=shuggart dd, 8= ibm ed,
                # 9=msx2 dd, 10=c64 dd, 11=emu shuggart, 12=s950 dd, 13=s950 hd
    1,          # 17
    0x001,      # 18 Offset of track LUT
    255,        # Write allowed
    255)        # Single/Double step
  data=bytearray()
  track_dat=[]
  track_siz=[]
  track_range=len(tracks)
  print ("Tracks:",track_range," Cyls:", cyls," Sides:", sides)
  for tr in range(cyls):
#  for tr in range(4):
#  for tr in range(80,81):
    data=bytearray()
 #   print(len(tracks_mfm),tr,sides)
    track_size1=len(tracks_mfm[tr*sides+0])
    if sides==2: track_size2=len(tracks_mfm[tr*sides+1])
    else: track_size2=track_size1
    if track_size1>track_size2: track_sz=track_size1
    else: track_sz=track_size2
    track_sz_align=((track_sz+255)//256)*256 #full aligned
    t_offs=0
#    print (track_size1,track_size2)
    while t_offs<track_sz_align:
      data.extend(tracks_mfm[tr*sides+0][t_offs:t_offs+0x100])
#      data[len(data)-1]=255
      togo=track_size1-t_offs
#      if tr>=80: print('\n0:ofs=%d tg=%d'%(t_offs,togo),end=' ')
      if togo>0 and togo<0x100:
        data.extend(bytearray([0x0,0x0]*(0x80-togo//2))) #tail
#        data.extend(tracks_mfm[tr*sides+0][0:(0x100-togo)]) #tail
#        if track_size1<0x80: data.extend(bytearray([0x2a,0x49]*(0x80-togo)))
      elif togo<=0:
        data.extend(bytearray([0x0,0x0]*0x80)) #over tail

      if sides==2:
        data.extend(tracks_mfm[tr*sides+1][t_offs:t_offs+0x100])
        togo=track_size2-t_offs
#        if tr>=80: print('1:ofs=%d tg=%d'%(t_offs,togo),end=' ')
        if togo>0 and togo<0x100:
          data.extend(bytearray([0x0,0x0]*(0x80-togo//2)))
#          data.extend(tracks_mfm[tr*sides+1][0:(0x100-togo)]) #tail
#          if track_size2<0x80: data.extend(bytearray([0,0]*(0x80-togo))) #0x05,0x11
        elif togo<=0:
          data.extend(bytearray([0x0,0x0]*0x80))
      else:
        data.extend(bytearray([0]*0x100)) #single sided empty
#      data[len(data)-1]=254
      t_offs+=0x100 #next 2 x 256bytes chunk
    track_dat.append(data)
#    if tr>=80: print(len(data),' ')
    track_siz.append(track_sz*2)
  data=bytearray()
  offset=2 #in 0x200 values
  for tr in range(cyls):
    data.append(offset&0xff)
    data.append((offset>>8)&0xff)
    data.append((track_siz[tr])&0xff)
    data.append((track_siz[tr]>>8)&0xff)
    offset+=len(track_dat[tr])//512
#    print(tr*2,tr*2+1,track_siz[tr]//4) #@!
  data.extend([0xff]*(512-len(data)))
#  print('total',len(data))
  print()
  print("Writing file.")
  with open(filename, "wb") as f:
    f.write(header)
    f.write(bytearray([255]*(512-22)))
    f.write(data)
    for tr in range(cyls):
      f.write(track_dat[tr])



#################################################################
def exportudi(filename):
  global tracks_mfm, tracks, syncs, sectors, cyls, sides, _CRC

  print ()
  print ("Exporting UDI file v1.0 \"%s\"..." %filename)
  data=bytearray()
  length=0
  track_range=len(tracks)
  print ("Tracks:",track_range," Cyls:", cyls," Sides:", sides)
  for tr in range(track_range):
    tlen=len(tracks[tr])
#    print(tr,tlen) #@!
    length+=(3+tlen+len(syncs[tr]))
    data+=struct.pack("<BH",0,tlen) #0=mfm
    data+=tracks[tr]
    data+=syncs[tr]

      
#    if len(sectors[tr])!=32: print(sectors[tr])
#    print('.',end='')
#  print(length)

  header = struct.pack("<4sI4BI",
    b"UDI!",   # Signature
    length+16, # File length - last 4 bytes of CRC (head+tracks)
    0,         # Version
    cyls-1,    # Cylinders-1 (0x4f=80)
    sides-1,   # Sides-1 (0=1side, 1=2sides, 3..ff-reserved
    0,         # unused
    0)         # EXTHDL size


  _CRC=0xffffffff
  print("Calculating CRC:",end="")
  udicrc(header)
  udicrc(data)
  print()
  print("Writing file.")
  with open(filename, "wb") as f:
    f.write(header)
    f.write(data)
    f.write(struct.pack("<I",_CRC))
#  print('%04x'%_CRC)
  


#################################################################

def _main(argv):
  print("UDIv1<->HFEv1 converter v0.2.20210302  (c) 2019-2021 by Denis Dratov")
  parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("infile", help="in filename")
  parser.add_argument("outfile", help="out filename")
  parser.add_argument("-resync", action="store_true", help="UDI: recover incomplete A1 syncs")
  parser.add_argument("-preserve", action="store_true", help="HFE,UDI: preserve desynced 4E/C2")
  args = parser.parse_args(argv[1:])

  infn, infn_ext = os.path.splitext(args.infile)
  outfn, outfn_ext = os.path.splitext(args.outfile)

  res=False
  if infn_ext.lower()=='.udi':
    res=importudi(args.infile,recover=args.resync,preserve=args.preserve)
  elif infn_ext.lower()=='.hfe':
    res=importhfe(args.infile,preserve=args.preserve)
  if res==False:
    print("Error importing \"%s\"" %args.infile)
    exit()
  
  if outfn_ext.lower()=='.udi':
    res=exportudi(args.outfile)
  elif outfn_ext.lower()=='.hfe':
    res=exporthfe(args.outfile)
  

  '''
  with open(args.file, "rb") as f:
    dat=f.read()
  global _CRC
  _CRC=0xffffffff
  udicrc(dat[0:-4])
  print("CALC=%08x"%_CRC)
  _CRC=struct.unpack("<I",dat[-4:])[0]
  print("FILE=%08x"%_CRC)
  '''

if __name__ == "__main__":
  _main(sys.argv)
