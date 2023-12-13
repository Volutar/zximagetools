# demfm.py v1.1c
#
# MFM bitstream parser/decoder
# Uses un-mirrored MFM representation
#
# Written by Denis Dratov aka Dexus <volutar@gmail.com>
#
# This is free and unencumbered software released into the public domain.
# See the file COPYING for more details, or visit <http://unlicense.org>.
import sys

def mirrbin(b):
  k=0
  for _ in range(8):
    k<<=1
    if b&1: k|=1
    b>>=1
  return bin(k)[2:].zfill(8).replace("0",".")

class DeMFM:
  """De-MFM and logical parse of unsynchronized MFM bitstream"""
  crctable = [] #shared list
  _curcrc = 0xffff
  bytes=bytearray()
  syncs=bytearray()
  cat=list()
  syncbreaks=0

  def __init__(self):
    poly = 0x1021
    if len(self.crctable)>0: #already created
      return
    for byte in range(256):
      w = byte << 8
      for _ in range(8):
        if (byte ^ w) & 0x8000:
          w = (w << 1) ^ poly
        else:
          w <<= 1
      w &= 0xffff
      self.crctable.append(w)

  @classmethod
  def crc16add(self,byte):
    self._curcrc = self.crctable[((self._curcrc >> 8) ^ byte) & 0xff] ^ (self._curcrc << 8) & 0xffff

  @staticmethod
  def unmfm(mfm):
    bt=0
    if mfm&0x0002: bt|=0x80
    if mfm&0x0008: bt|=0x40
    if mfm&0x0020: bt|=0x20
    if mfm&0x0080: bt|=0x10
    if mfm&0x0200: bt|=0x08
    if mfm&0x0800: bt|=0x04
    if mfm&0x2000: bt|=0x02
    if mfm&0x8000: bt|=0x01
    return bt

# deshuffle odd/even array in amiga manner
  @staticmethod
  def ami_unshuffle(bytes,start,ln):
    rt=bytearray()
    p1=start
    p2=start+ln
    for _ in range(ln):
      a1=bytes[p1]
      a2=bytes[p2]
      dec=0
      for _ in range(8):
        dec<<=2
        if a1&0x80: dec|=2
        if a2&0x80: dec|=1
        a1<<=1
        a2<<=1
      rt.append(dec>>8)
      rt.append(dec&0xff)
      p1+=1
      p2+=1
    return rt

# shuffle odd/even array in amiga manner
  @staticmethod
  def ami_shuffle(bytes,start,ln):
    rt1=bytearray()
    rt2=bytearray()
    p1=start
    for _ in range(ln):
      dec=(bytes[p1]<<8) | bytes[p1+1]
      a1=a2=0
      for _ in range(8):
        a1<<=1
        a2<<=1
        if dec&0x8000: a1|=1
        if dec&0x4000: a2|=1
        dec<<=2
      rt1.append(a1)
      rt2.append(a2)
      p1+=2
    return rt1+rt2


# Main MFM decoding and parsing procedure
# in:
#  mfm encoded byte list
# out:
#  -bytes = decoded byte list (synced)
#  -syncs = bitmap (1 bit per byte, val = (syncs[x//8]>>(x%8))&1)
#  -cat = track catalog structure (to use with additional parsing and converting):
#    -type: 1=IDAM, 2=DAM -1=unknown
#    -id: sync ID (FB/FE)
#    -offset: data offset in decoded byte list
#    -datalen: data length in decoded byte list (and CRC after, if not interrupted)
#    -crc: CRC 1=OK 0=BAD -1=NO CRC (early interruption)
#    -cylinder: 0-84 (taken from IDAM)
#    -side: 0-1      (taken from IDAM - not reliable on ZX)
#    -sector: 0-255
#
  @classmethod
  def decode_mfm(self,dat,justcat=False,recover=False,preserve=False):
    self.bytes=bytearray()
    self.syncs=bytearray()
    self.cat=[]
    self.syncbreaks=0
    curbyte=0
    bit=16
    bit_old=0
    mark=0
    mark2=0
    sync=0
    sync_cnt=8
    runstage=0
    runarea=0
    readcrc=0
    cur_type=0
    cur_id=0
    cur_offset=0
    cur_cyl=0
    cur_side=0
    cur_sec=0
    cur_seclen=0
    idx=-1
#    runbit=0
    amiga=False
    amibuf=bytearray()
    amidec=bytearray()

    for x in dat:
      idx+=1
      for b in range(8):
        prevcur=curbyte&1 #prevbit
        curbyte>>=1
        if x&0x01: curbyte|=0x8000
        x>>=1
        bit-=1

##################################
        # Gap syncs
        if runstage==0:
          if not preserve or bit==0:
            if curbyte==0x2a49: #2a49 0x9254:#1001001001010100 #sync gap 4E
              bit_old=bit
              if bit!=0:
  #              print('(=%d,%d)'%(bit,idx),end='')
                bit=0
                mark=0 
                mark2=2
            elif curbyte==0x244a: #0x5224: #1010010001001000 #sync C2
              bit_old=bit
              bit=0
              mark=2

          # Fixing pre-A1 zeros
          if curbyte==0x9122: #0x4489: #0100010010001001 #sync A1
            k=0
            z=-1
            #traversing back from sync
            # probably we need to make similar stuff for UDI, and only for A1A1A1
            if not recover and not preserve:
              for y in range(2,24,2): 
#                if len(self.bytes)<12: break
#                if idx-y<0: j=0
#                else: j=dat[idx-y]
                k=(dat[idx-y]<<16) + (dat[idx-y-1]<<8) + (dat[idx-y-2]<<0)
                k=(k>>(b+1))&0xffff

#                print('#%.4x ' %k,end='')
                if y>0: #fixing pre-sync 0x00 to proper 0x00
                  l=self.unmfm(k)
                  z-=1
                  if len(self.bytes)<-z: break
#                  print('#%.2x %d ' %(l,z),end='')
                  if l==0: self.bytes[z]=0
                  elif z==-13 and l&0x3f==0:
                    self.bytes[z]=0 #first byte of 12x0 may be incomplete
                  elif len(self.bytes)==-z and l&0x0f==0:
                    self.bytes[z]=0
                  else:
                    break
#              print()


        # Any stage
        if curbyte==0x9122: #0x4489: #0100010010001001 #sync A1
          bit_old=bit
          bit=0
          mark=1
          if runarea>0 and runstage>3: #ISSUE: sync inside data, early stop
            runstage=0 
            self.cat.append([cur_type,cur_id,cur_offset,len(self.bytes)-cur_offset,-1,cur_cyl,cur_side,cur_sec])
          if runstage==4:
            runstage=0
          elif runstage==3:
            runstage=0
          elif runstage==2:
            runstage=3
          elif runstage==1:
            runstage=2
          elif runstage==0:
            self._curcrc=0xffff #init crc
            readcrc=0
            runarea=4+4+2
            runstage=1
#            print('\nSYNC: ',end='')
        elif bit==0: #other than A1
          if runstage>=1 and runstage<=2:
            if recover:
              if runstage==2:
                l=self.unmfm(curbyte)
                if l>=0xf8 and l<=0xfe:
#                  print("[%02x]"%l,end=' ')
                  self._curcrc=0xcdb4 #after a1a1a1
                  readcrc=0
                  runarea=4+4+2
                  runstage=4
                  if sync_cnt<6:
                    sync|=0xe0
                  elif sync_cnt>=6:
                    self.syncs[-1]|=(0xe0<<(8-sync_cnt))&0xff #add prev A1 sync
#                    sw=0x80>>(ty-8)
#                    sync|=sw
#                  print("#%02x #%02x %d:"%(sync,self.syncs[-1],sync_cnt))
                   
                  for y in range(1,16):
                    midx=len(self.bytes)-y
                    if y<=3:
                      self.bytes[midx]=0xa1
                    else:
                      self.bytes[midx]=0x00

#                    print("%02X"%self.bytes[-y],end='-')
#                  print()
            else:
              if runstage==2: #amiga disk
#                print('amiga')
                amiga=True
                amibuf=bytearray()
                cur_offset=len(self.bytes)
#                print('offs',cur_offset)
#                runarea=20+2+2+512+4
                runarea=4
                runstage=4
              else:
#                print('SYNC break',runstage,len(self.bytes))
                self.syncbreaks+=1
                runstage=0
                runarea=0
   
#        if preserve and bit==0:
#          if bit_old==14 and mark==0 and curbyte==0x2a49: #special case of false 0x4e
#            curbyte=curbyte&0xfffe #mask it not to multply 0x4e area
#            bit=bit_old #skip sync

        if bit==0:
          bit=16
          decbyte=self.unmfm(curbyte)
#          print("%04X-%02X"%(curbyte,decbyte),end=' ')
#        print(format(decbyte,'02X'),end=' ')
          '''
          print("%s%s%s%s|"%(
          mirrbin(dat[idx-1]),
          mirrbin(dat[idx]),
          mirrbin(dat[idx+1]),
          mirrbin(dat[idx+2])),end='')
          '''

          #sync bit map
          sync>>=1
          if mark==1:
            if mark2==1: #deal with A1, if it was false C2 beforehand
              self.bytes.pop() #very tricky equilibristics, trying not to screw it
              if sync_cnt==8:  #removing C2 and replacing it with A1
                sync=self.syncs.pop()
                sync_cnt=0
              sync_cnt+=1
              sync<<=1
            mark2=0
            sync|=0x80
          elif mark==2: #C2
            mark2=1
            sync|=0x80
            
          self.bytes.append(decbyte)
          mark=0
          bit_old=0
          sync_cnt-=1
          if sync_cnt==0:
            self.syncs.append(sync&0xff)
            sync_cnt=8
        else:
          continue #between bytes --------^

#        if idx>=0xc80*2 and idx<=0xd80*2:
#          print("%02X"%(decbyte),end=' ')

				   #bytes aligned --------v
        if amiga:
#                runarea=20+2+2+512+4
#                for i in range(0,22+2,2):
#                for i in range(26,26+2+512,2):
#                self.cat.append([1,1,cur_offset,22,cur_crc,cur_cyl,cur_side,cur_sec])
#                self.cat.append([2,2,cur_offset+28,512,cur_crc,cur_cyl,cur_side,cur_sec])
          if runstage==4: #header
            if runarea==0:
              amidec=self.ami_unshuffle(amibuf,0,2)
              if amidec[0]!=0xff or amidec[2]>21 or amidec[3]>21: #skip - not amiga!
                amiga=False
                runstage=0
                runarea=0
#                print('4: %d, not amiga' %(len(amibuf)))
              else:
                cur_cyl=amidec[1]//2
                cur_side=amidec[1]%2
                cur_sec=amidec[2]
#                print('4: %d, %04X' %(len(amibuf),self._curcrc))
#                print(' - %02x:%d %02x' %(cur_cyl,cur_side,cur_sec))
                runstage=5
                runarea=20
            else: #if runarea>0:
              amibuf.append(decbyte)
              runarea-=1
#              print('4+',end='')
          if runstage==5: #header
            if runarea==0:
              #use CRC bytes as CRCed data, so it should compensate to 0
              self._curcrc=0
              for i in range(0,4+20,2):
                self._curcrc^=((amibuf[i]<<8)+amibuf[i+1])
              if self._curcrc==0: cur_crc=1 #header crc - offset 22,23
              else: cur_crc=0
#              print('5: %d, %04X' %(len(amibuf),self._curcrc))
              self.cat.append([1,1,cur_offset,22,cur_crc,cur_cyl,cur_side,cur_sec])
    
              runstage=6
              runarea=512+4
            else: #if runarea>0:
              amibuf.append(decbyte)
              runarea-=1
#              print('5+',end='')
    
          if runstage==6:
            if runarea==0:
#              self._curcrc=(amibuf[26]<<8)+amibuf[27]
#              print(' %04X' %(self._curcrc))
              self._curcrc=0
              for i in range(4+20+2,4+20+2+2+512,2):
                self._curcrc^=((amibuf[i]<<8)+amibuf[i+1])
              if self._curcrc==0: cur_crc=1 #header crc - offset 26,27
              else: cur_crc=0
#              print('6: %d, %04X' %(len(amibuf),self._curcrc))
              self.cat.append([2,2,cur_offset+4+20+2+2,512,cur_crc,cur_cyl,cur_side,cur_sec])
              '''
              amidec=self.ami_unshuffle(amibuf,28,256) #unshuffle
              #update received bytearray with unshuffled sector data
              for i in range(len(amidec)):
#                print(format(amidec[i],'02X'),end=' ')
                self.bytes[-513+i]=amidec[i]
              '''
#              for i in range(cur_offset+28,cur_offset+28+32):
#                ch=self.bytes[i]
#                print(f"{ch:02x} ",end='')
              runstage=0
            else: #if runarea>0:
              amibuf.append(decbyte)
              runarea-=1
#              if runstage<24:
    
        elif runstage>0:
          if runstage==8: #seclen
            cur_seclen=128*(1<<(decbyte&7)) # &3 would emulate 2bit WD1772 behavior
#            print(f'(IDAM cyl={cur_cyl} side={cur_side} sec={cur_sec} seclen={cur_seclen})',end='')
            runstage+=1
          elif runstage==7: #sec
            cur_sec=decbyte
            runstage+=1
          elif runstage==6: #side
            cur_side=decbyte
            runstage+=1
          elif runstage==5: #IDAM -> cyl
            cur_cyl=decbyte
            runstage+=1
          elif runstage==4: #after A1 sync 
            cur_offset=len(self.bytes)
            cur_id=decbyte
            if decbyte>=0xfc: #IDAM
              cur_type=1
              runarea=4+3
              runstage+=1
            elif decbyte>=0xf8: #DAM
              cur_type=2
##              print(f'(DAM {len(bytes)}: {cur_seclen} bytes)')
              if cur_seclen==0: #displaced DAM
                runstage=-1
              else:
                runarea=cur_seclen+3
                runstage=9
            else:  #illegal code (not fb-ff)
              cur_type=-1
              runstage=0
          elif runstage==3: #skip third A1
            runstage+=1
    
          if cur_type==-1: #unknown sync type
            self.cat.append([cur_type,cur_id,cur_offset,0,0,0,0,0])
            cur_type=0
    
          if runarea==1: #CRC collected
            readcrc|=decbyte
            if readcrc==self._curcrc:
#              print('OK!')
              cur_crc=1
            else:
              cur_crc=0
#              print("BAD({:04X})".format(self._curcrc))
            if cur_type==1:
              datalen=4
            else:
              datalen=cur_seclen
            self.cat.append([cur_type,cur_id,cur_offset,datalen,cur_crc,cur_cyl,cur_side,cur_sec])
            curbyte=0 #to avoid false C2* after CRC
#              cur_cyl=0
#              cur_side=0
#              cur_sec=0
#              cur_seclen=0 #only once
            cur_type=0 #clear catalog item id
            cur_id=0
            runstage=0
            runarea=0 
          elif runarea==2: #first byte of CRC
            readcrc=decbyte<<8
            runarea=1
#          if runarea==3: #data is over - CRC data begin
#            print('\nCRC: ',end='')
          elif runarea>=3:
            self.crc16add(decbyte) #calculating running CRC
            runarea-=1

##################################
#    print("\n")
#    for idx in range(0xfff):
#      if idx>=0xc80 and idx<=0xd80:
#        print("%02X"%(self.bytes[idx]),end=' ')

    if sync_cnt>0 and sync_cnt<8: #sync bitmap leftovers
      while sync_cnt>0:
        sync_cnt-=1
        sync>>=1
      self.syncs.append(sync)

    if runstage!=0: #unfinished chunk
#      print(runstage,runarea,cur_offset)
      self.cat.append([cur_type,cur_id,cur_offset,len(self.bytes)-cur_offset,-1,cur_cyl,cur_side,cur_sec])

#    if len(self.cat)==0 and amiga:
#      self.cat.append(['ami'])
    '''
    for x in range(0,len(self.bytes)):
      print(" {:02X}".format(self.bytes[x]),end="")
      if (self.syncs[x//8]>>(x%8))&1: print(".",end="")
    '''
#  print('\n')
#    return self.bytes,self.syncs,self.cat
#    print(format(x,"02X"),end=" ")

#####################################################################
  def print_cat(self):
    for i in self.cat:
      if i[0]=="ami": break
      if i[0]==2: s="\t"
      else: s=""
      print(s,end="")
      k=i[3]
      if k>8: k=8
      for j in range(k):
        print("{:02X}".format(self.bytes[i[2]+j]),end=" ")
      print("-",i)
#      print(s,end='')

#    for x in range(0,len(self.bytes)):
#      print(format(self.bytes[x],"02X"),end=" ")
#      print((self.syncs[x//8]>>(x%8))&1,end=" ")

    print ("len=",len(self.bytes))
    print

#####################################################################
  def print_cat_short(self):
    cyl=-1
    side=-1
    sec=-1
    slen=-1

#    for x in range(0,len(self.bytes)):
#      print(" {:02X}".format(self.bytes[x]),end="")
#      if (self.syncs[x//8]>>(x%8))&1: print(".",end="")

#    head=False
    for i in self.cat:
#      if i[0]=='ami':
#        print('Amiga track')
#        return
      if i[0]==1: #IDAM
        if cyl!=i[5] or side!=i[6]:
          cyl=i[5]
          side=i[6]
          print (f"T{cyl:03}:{side}",end=" ")
        sec=i[7]
#        head=True
      if i[0]==2: #DAM
        if slen==-1:
          print (f"len{i[3]}",end="  ")
          slen=i[3]

        if sec>=0: ssec=format(sec,"02X")
        else: ssec="_"
        if slen!=i[3]:
          print(f"[{i[3]}]",end="")
        if i[4]==1: #CRC ok
          print(f"{ssec}", end=" ")
        elif i[4]==0: #CRC error
          print(f"{ssec}!", end=" ")
        elif i[4]==-1: #broken sector
          print(f"{ssec}\\", end=" ")
        sec=-1

    print()
#    print ('bytes:',sys.getsizeof(self.bytes))
#    print ('syncs:',sys.getsizeof(self.syncs))
#    print ('cat:',sys.getsizeof(self.cat))
