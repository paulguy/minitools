import struct
import binascii
import os
import argparse

MEDIA_BLOCK_SIZE = 0x200
KILOBYTE = 1024
MEGABYTE = 1024**2
GIGABYTE = 1024**3

spoof = 0
i = 0

sysCalls = (
  'Unknown',
  'ControlMemory',
  'QueryMemory',
  'ExitProcess',
  'GetProcessAffinityMask',
  'SetProcessAffinityMask',
  'SetProcessIdealProcessor',
  'GetProcessIdealProcessor',
  'CreateThread',
  'ExitThread',
  'SleepThread',
  'GetThreadPriority',
  'SetThreadPriority',
  'GetThreadAffinityMask',
  'SetThreadAffinityMask',
  'GetThreadIdealProcessor',
  'SetThreadIdealProcessor',
  'GetCurrentProcessorNumber',
  'Run',
  'CreateMutex',
  'ReleaseMutex',
  'CreateSemaphore',
  'ReleaseSemaphore',
  'CreateEvent',
  'SignalEvent',
  'ClearEvent',
  'CreateTimer',
  'SetTimer',
  'CancelTimer',
  'ClearTimer',
  'CreateMemoryBlock',
  'MapMemoryBlock',
  'UnmapMemoryBlock',
  'CreateAddressArbiter',
  'ArbitrateAddress',
  'CloseHandle',
  'WaitSynchronization1',
  'WaitSynchronizationN',
  'SignalAndWait',
  'DuplicateHandle',
  'GetSystemTick',
  'GetHandleInfo',
  'GetSystemInfo',
  'GetProcessInfo',
  'GetThreadInfo',
  'ConnectToPort',
  'SendSyncRequest1',
  'SendSyncRequest2',
  'SendSyncRequest3',
  'SendSyncRequest4',
  'SendSyncRequest',
  'OpenProcess',
  'OpenThread',
  'GetProcessId',
  'GetProcessIdOfThread',
  'GetThreadId',
  'GetResourceLimit',
  'GetResourceLimitLimitValues',
  'GetResourceLimitCurrentValues',
  'GetThreadContext',
  'Break',
  'OutputDebugString'
)

# An unknown attribute is documented but not supported by makerom
FSAccessInfo = (
  'CategorySystemApplication',
  'CategoryHardwareCheck',
  'CategoryFileSystemTool',
  'Debug',
  'TwlCardBackup',
  'TwlNandData',
  'Boss',
  'DirectSdmc',
  'Core',
  'CtrNandRo',
  'CtrNandRw',
  'CtrNandRoWrite',
  'CategorySystemSettings',
  'CardBoard',
  'ExportImportIvs',
  'DirectSdmcWrite',
  'SwitchCleanup',
  'SaveDataMove',
  'Shop',
  'Shell',
  'CategoryHomeMenu'
)

# SD Application (8) is set by Options/UseOnSD
# Mount sdmc:/ (9) is set by FileSystemAccess flags
ARM9Access = (
  'FsMountNand',
  'FsMountNandRoWrite',
  'FsMountTwln',
  'FsMountWnand',
  'FsMountCardSpi',
  'UseSdif3',
  'CreateSeed',
  'UseCardSpi',
)

rsffile = {
  'Option': {
    'UseOnSD': 'True',
    'EnableCompress': 'True',
    'FreeProductCode': 'True',
    'EnableCrypt': 'False',
    'MediaFootPadding': 'False'
  }, 'AccessControlInfo': {
    'DisableDebug': '',
    'EnableForceDebug': '',
    'CanWriteSharedPage': '',
    'CanUsePrivilegedPriority': '',
    'CanUseNonAlphabetAndNumber': '',
    'PermitMainFunctionArgument': '',
    'CanShareDeviceMemory': '',
    'RunnableOnSleep': '',
    'SpecialMemoryArrange': '',
    'UseOtherVariationSaveData': '',
    'CanAccessCore2': '',
    'UseExtSaveData': '',
    'EnableL2Cache': '',
    'IdealProcessor': '',
    'Priority': '',
    'MemoryType': 'Application',
    'SystemMode': '',
    'SystemModeExt': '',
    'CpuSpeed': '',
    'CoreVersion': '',
    'HandleTableSize': '',
    'SystemSaveDataId1': '',
    'SystemSaveDataId2': '',
    'OtherUserSaveDataId1': '',
    'OtherUserSaveDataId2': '',
    'OtherUserSaveDataId3': '',
    'ExtSaveDataId': '',
    'AffinityMask': '',
    'DescVersion': '',
    'ResourceLimitCategory': '',
    'ReleaseKernelMajor': '',
    'ReleaseKernelMinor': '',
    'MaxCpu': '',
    'MemoryMapping': [],
    'IORegisterMapping': [],
    'FileSystemAccess': [],
    'IoAccessControl': [],
    'InterruptNumbers': [],
    'SystemCallAccess': [],
    'ServiceAccessControl': [],
    'AccessibleSaveDataIds': []
  }, 'SystemControlInfo': {
    'StackSize': '',
    'RemasterVersion': '',
    'JumpId': '',
    'SaveDataSize': '',
    'Dependency': []
  }, 'BasicInfo': {
    'Title': '',
    'CompanyCode': '',
    'ProductCode': '',
    'ContentType': 'Application',
    'Logo': 'Nintendo'
  }, 'RomFs': {
    'RootPath': '',
  }, 'TitleInfo': {
    'Category': 'Application',
    'UniqueId': ''
  }
}

# Lists that require there to not be a dash
specialLists = [
  'AccessControlInfo/SystemCallAccess',
  'SystemControlInfo/Dependency'
]


# NOTE: TitleInfo is all from the Program ID field in the NCCH header
# Version, ContentsIndex, Variation, ChildIndex and DemoIndex all are the
# "Variation" byte in different contexts.  None of them do anything for
# Applications.
# TargetCategory sets Category in the case of constructing an exheader.  Not
# sure about the specific details, but Category should always work.
# CategoryFlags sets more specific flags.  Category can't be set at the same
# time.

# https://www.3dbrew.org/wiki/NCSD

# NCSD header
# Offset  Size          Description
# 0x000   0x100         RSA-2048 SHA-256 signature of the NCSD header (rsasig)
# 0x100   4             Magic Number 'NCSD' (magic)
# 0x104   4             Size of the NCSD image, in media units (1 media unit = 0x200 bytes) (mediasize)
# 0x108   8             Media ID (mediaid)
# 0x110   8             Partitions FS type (0=None, 1=Normal, 3=FIRM, 4=AGB_FIRM save) (type)
# 0x118   8             Partitions crypt type (crypttype)
# 0x120   0x40=(4+4)*8  Offset & Length partition table, in media units (offsets lenghts)
# 0x160   0xA0          ...

# For carts,
# Offset 	Size      Description
# 0x160   0x20      Exheader SHA-256 hash (exhdrhash)
# 0x180   0x4       Additional header size (addhdrsize)
# 0x184   0x4       Sector zero offset (zerooffset)
# 0x188   8         Partition Flags (See Below) (flags)
# 0x190   0x40=8*8  Partition ID table (partids)
# 0x1D0   0x30      Reserved
# 0x200   0xE       Reserved?
# 0x20E   0x1       Support for this was implemented with 9.6.0-X FIRM. Bit0=1 enables using bits 1-2, it's unknown what these two bits are actually used for(the value of these two bits get compared with some other value during NCSD verification/loading). This appears to enable a new, likely hardware-based, antipiracy check on cartridges. (exflags)
# 0x20F   0x1       Support for this was implemented with 9.6.0-X FIRM, see below regarding save crypto.  (savecrypto)
ncsdHdrStruct = struct.Struct("<256s4sIQQQ16I32sIIQ8Q62xBB")

# https://www.3dbrew.org/wiki/NCCH

# NCCH Header
# OFFSET  SIZE  DESCRIPTION
# 0x000   0x100 RSA-2048 signature of the NCCH header, using SHA-256. (rsasig)
# 0x100   4     Magic ID, always 'NCCH' (magic)
# 0x104   4     Content size, in media units (1 media unit = 0x200 bytes) (mediasize)
# 0x108   8     Partition ID (partitionid)
# 0x110   2     Maker code (makercode)
# 0x112   2     Version (version)
# 0x114   4     When ncchflag[7] = 0x20 starting with FIRM 9.6.0-X, this is compared with the first output u32 from a SHA256 hash. The data used for that hash is 0x18-bytes: <0x10-long title-unique content lock seed> <programID from NCCH+0x118>. This hash is only used for verification of the content lock seed, and is not the actual keyY. (lockhash)
# 0x118   8     Program ID (programid)
# 0x120   0x10  Reserved
# 0x130   0x20  Logo Region SHA-256 hash. (For applications built with SDK 5+) (Supported from firmware: 5.0.0-11) (logohash)
# 0x150   0x10  Product code (productcode)
# 0x160   0x20  Extended header SHA-256 hash (SHA256 of 2x Alignment Size, beginning at 0x0 of ExHeader) (exhdrhash)
# 0x180   4     Extended header size (exhdrsize)
# 0x184   4     Reserved
# 0x188   8     Flags (See Below) (flags)
# 0x190   4     Plain region offset, in media units (plainoffset)
# 0x194   4     Plain region size, in media units (plainsize)
# 0x198   4     Logo Region offset, in media units (For applications built with SDK 5+) (Supported from firmware: 5.0.0-11) (logooffset)
# 0x19c   4     Logo Region size, in media units (For applications built with SDK 5+) (Supported from firmware: 5.0.0-11) (logosize)
# 0x1A0   4     ExeFS offset, in media units (exefsoffset)
# 0x1A4   4     ExeFS size, in media units (exefssize)
# 0x1A8   4     ExeFS hash region size, in media units (exefshashsize)
# 0x1AC   4     Reserved
# 0x1B0   4     RomFS offset, in media units (romfsoffset)
# 0x1B4   4     RomFS size, in media units (romfssize)
# 0x1B8   4     RomFS hash region size, in media units (romfshashsize)
# 0x1BC   4     Reserved
# 0x1C0   0x20  ExeFS superblock SHA-256 hash - (SHA-256 hash, starting at 0x0 of the ExeFS over the number of media units specified in the ExeFS hash region size) (exefssuperhash)
# 0x1E0   0x20  RomFS superblock SHA-256 hash - (SHA-256 hash, starting at 0x0 of the RomFS over the number of media units specified in the RomFS hash region size) (romfssuperhash)
ncchHdrStruct = struct.Struct("<256s4sIQ2sHIQ16x32s16s32sI4xQIIIIIII4xIII4x32s32s")

# https://www.3dbrew.org/wiki/NCCH/Extended_Header

# System Control Info
# Offset  Size          Description
# 0x0     0x8           Application Title (title)
# 0x8     0x5           Reserved
# 0xD     0x1           Flag (Bit0: CompressExefsCode, Bit1: SDApplication) (flag)
# 0xE     0x2           Remaster Version (remaster)
# 0x10    0xC           Text Code Set Info (textaddr textpages textsize)
# 0x1C    0x4           Stack Size (stack)
# 0x20    0xC           ReadOnly Code Set Info (roaddr ropages rosize)
# 0x2C    0x4           Reserved
# 0x30    0xC           Data Code Set Info (dataaddr datapages datasize)
# 0x3C    0x4           BSS Size (bsssize)
# 0x40    0x180 (48*8) 	Dependency Module (Program ID) List (dependencies)
# 0x1C0   0x40          SystemInfo (savesize jumpid)

# Code Set Info
# Offset  Size  Description
# 0x0     0x4   Address
# 0x4     0x4   Physical region size (in page-multiples)
# 0x8     0x4   Size (in bytes)

# System Info
# Offset  Size  Description
# 0x0     0x8   SaveData Size 
# 0x8     0x8   Jump ID
# 0x10    0x30  Reserved 
sysCtrlInfoStruct = struct.Struct("<8s5xBHIIIIIII4xIIII48QQQ48x")

# Access Control Info
# Offset 	Size 	Description
# 0x0     0x170 ARM11 Local System Capabilities
# 0x170   0x80  ARM11 Kernel Capabilities
# 0x1F0   0x10  ARM9 Access Control

# ARM11 Local System Capabilities
# Offset 	Size          Description
# 0x0     0x8           Program ID (programid)
# 0x8     0x4           Core Version (The Title ID low of the required FIRM) (corever)
# 0xC     0x1           Flag1 (1b l2cache, 1b cpuspeed, 6b nothing) (flag1)
# 0xD     0x1           Flag2 (4b sysmodeext 0='Legacy' 1='124MB' 2='178MB' (dev unit?)) (flag2)
# 0xE     0x1           Flag0 (flag0)
# 0xF     0x1           Priority (priority)
# 0x10    0x20 (16*2)   Resource Limit Descriptors (reslimits)
# 0x30    0x20          Storage Info (extdataid syssaveid(1,2) storageid fsaccess otherattrib)
# 0x50    0x100 (32*8)  Service Access Control (services)
# 0x150   0x10 (2*8)    Extended Service Access Control, support for this was implemented with 9.3.0-X. (services)
# 0x160   0xF           Reserved
# 0x16F   0x1           Resource Limit Category. (0 = APPLICATION, 1 = SYS_APPLET, 2 = LIB_APPLET, 3 = OTHER(sysmodules running under the BASE memregion)) (category)

# ARM11 Kernel Capabilities
# Offset  Size        Description
# 0x0     0x70 (28*4) Descriptors (kernelcaps)
# 0x70    0x10        Reserved 

# ARM9 Access Control
# Offset  Size  Description
# 0x0     0xF   Descriptors (arm9caps)
# 0xF     0x1   ARM9 Descriptor Version. Originally this value had to be >=2. Starting with 9.3.0-X this value has to be either value 2 or value 3. (arm9ver)

# Storage Info
# Offset  Size  Description
# 0x0     0x8   Extdata ID
# 0x8     (2*4) System Save Data Ids
# 0x10    0x8   Storage Accessable Unique Ids
# 0x18    0x7   File System Access Info
# 0x1F    0x1   Other Attributes 

# I implemented ARM9 Access Control as 'I11xB' instead of the documented 15 bytes
# field since this makes it easier, and makerom treats tha field as a 32 bit
# value anyway.
accCtrlInfoStruct = struct.Struct("<QIBBBB16HQQQQ272s15xB28I16xI11xB")

def makeNcsdHdrDictFromTuple(buffer):
  return({
    'rsasig': buffer[0],
    'magic': buffer[1],
    'mediasize': buffer[2],
    'mediaid': buffer[3],
    'type': buffer[4],
    'crypttype': buffer[5],
    'offsets': tuple(buffer[6:22][x] for x in range(0, 16, 2)), # 6 + 16
    'lengths': tuple(buffer[6:22][x] for x in range(1, 16, 2)),
    'exhdrhash': buffer[22],
    'addheadersize': buffer[23],
    'zerooffset': buffer[24],
    'flags': buffer[25],
    'partids': range(26, 33), # 26 + 8
    'exflags': buffer[34],
    'savecrypto': buffer[35]
  })
    
def makeNcchHdrDictFromTuple(buffer):
  return({
    'rsasig': buffer[0],
    'magic': buffer[1],
    'mediasize': buffer[2],
    'partitionid': buffer[3],
    'makercode': buffer[4],
    'version': buffer[5],
    'lockhash': buffer[6],
    'programid': buffer[7],
    'logohash': buffer[8],
    'productcode': buffer[9],
    'exhdrhash': buffer[10],
    'exhdrsize': buffer[11],
    'flags': buffer[12],
    'plainoffset': buffer[13],
    'plainsize': buffer[14], 
    'logooffset': buffer[15],
    'logosize': buffer[16],
    'exefsoffset': buffer[17],
    'exefssize': buffer[18],
    'exefshashsize': buffer[19], 
    'romfsoffset': buffer[20],
    'romfssize': buffer[21],
    'romfshashsize': buffer[22],
    'exefssuperhash': buffer[23],
    'romfssuperhash': buffer[24]
  })

def makeSysCtrlInfoDictFromTuple(buffer):
  return({
    'title': buffer[0],
    'flag': buffer[1],
    'remaster': buffer[2],
    'textaddr': buffer[3],
    'textpages': buffer[4],
    'textsize': buffer[5],
    'stack': buffer[6],
    'roaddr': buffer[7],
    'ropages': buffer[8],
    'rosize': buffer[9],
    'dataaddr': buffer[10],
    'datapages': buffer[11],
    'datasize': buffer[12],
    'bsssize': buffer[13],
    'dependencies': buffer[14:62], # 14 + 48
    'savesize': buffer[62],
    'jumpid': buffer[63]
  })

def makeAccCtrlInfoDictFromTuple(buffer):
  return({
    'programid': buffer[0],
    'corever': buffer[1],
    'flag1': buffer[2],
    'flag2': buffer[3],
    'flag0': buffer[4],
    'priority': buffer[5],
    'reslimits': buffer[6:22],
    'extdataid': buffer[22],
    'syssaveid1': buffer[23] >> 0  & 0xFFFFFFFF,
    'syssaveid2': buffer[23] >> 32 & 0xFFFFFFFF,
    'storageid': buffer[24],
    'fsaccess': buffer[25] & 0xFFFFFFFFFFFFFF,
    'otherattrib': buffer[25] >> 56 & 0xFF,
    'services': tuple(buffer[26][x:x+8] for x in range(0, 272, 8)), # 34 entries of 8 bytes each
    'category': buffer[27],
    'kernelcaps': buffer[28:56], # 28 + 28
    'arm9caps': buffer[56],
    'arm9ver': buffer[57]
  })


def warning(warning):
  print("WARNING: %s" % warning, file=sys.stderr)


def populateRSFFile():
  # AccessControlInfo
  
  # handle those annoying ARM11 Kernel Capabilities values
  for caps in accCtrlInfo['kernelcaps']:
    # InterruptNumbers
    # each has 4 interrupts packed in, 7 bits each
    if caps & 0xF0000000 == 0xE0000000:
      ints = (caps >> 0 & 0x7F, caps >> 7 & 0x7F, caps >> 14 & 0x7F, caps >> 21 & 0x7F)
      for intr in ints:
        if intr == 0:
          break
        rsffile['AccessControlInfo']['InterruptNumers'].append(intr)
    # SystemCallAccess
    # first 3 bits after the descriptor value indicate a group of 24 syscalls
    # the next 24 bits are a mask for this group.
    elif caps & 0xF8000000 == 0xF0000000:
      scstart = (caps >> 24 & 0x7) * 24
      for sc in enumerate(sysCalls[scstart:scstart+24]):
        if caps & (1 << sc[0]) != 0:
          rsffile['AccessControlInfo']['SystemCallAccess']\
            .append("%s: %d" % (sc[1], scstart + sc[0]))
    # ReleaseKernelMajor, ReleaseKernelMinor
    elif caps & 0xFE000000 == 0xFC000000:
      rsffile['AccessControlInfo']['ReleaseKernelMinor'] = caps >> 0 & 0xFF
      rsffile['AccessControlInfo']['ReleaseKernelMajor'] = caps >> 8 & 0xFF
    # HandleTableSize
    elif caps & 0xFF000000 == 0xFE000000:
      rsffile['AccessControlInfo']['HandleTableSize'] = caps & 0x7FFFF
    # DisableDebug, EnableForceDebug, CanWriteSharedPage, CanUsePrivilegedPriority,
    # CanUseNonAlphabetAndNumber, PermitMainFunctionArgument, CanShareDeviceMemory,
    # RunnableOnSleep, SpecialMemoryArrange
    elif caps & 0xFF800000 == 0xFF000000:
      if caps & 0x1 != 0:
        rsffile['AccessControlInfo']['DisableDebug'] = 'False'
      else:
        rsffile['AccessControlInfo']['DisableDebug'] = 'True'
      if caps & 0x2 != 0:
        rsffile['AccessControlInfo']['EnableForceDebug'] = 'True'
      else:
        rsffile['AccessControlInfo']['EnableForceDebug'] = 'False'
      if caps & 0x4 != 0:
        rsffile['AccessControlInfo']['CanUseNonAlphabetAndNumber'] = 'True'
      else:
        rsffile['AccessControlInfo']['CanUseNonAlphabetAndNumber'] = 'False'
      if caps & 0x8 != 0:
        rsffile['AccessControlInfo']['CanWriteSharedPage'] = 'True'
      else:
        rsffile['AccessControlInfo']['CanWriteSharedPage'] = 'False'
      if caps & 0x10 != 0:
        rsffile['AccessControlInfo']['CanUsePrivilegedPriority'] = 'True'
      else:
        rsffile['AccessControlInfo']['CanUsePrivilegedPriority'] = 'False'
      if caps & 0x20 != 0:
        rsffile['AccessControlInfo']['PermitMainFunctionArgument'] = 'True'
      else:
        rsffile['AccessControlInfo']['PermitMainFunctionArgument'] = 'False'
      if caps & 0x40 != 0:
        rsffile['AccessControlInfo']['CanShareDeviceMemory'] = 'True'
      else:
        rsffile['AccessControlInfo']['CanShareDeviceMemory'] = 'False'
      if caps & 0x80 != 0:
        rsffile['AccessControlInfo']['RunnableOnSleep'] = 'True'
      else:
        rsffile['AccessControlInfo']['RunnableOnSleep'] = 'False'
      if caps & 0x800 != 0:
        rsffile['AccessControlInfo']['SpecialMemoryArrange'] = 'True'
      else:
        rsffile['AccessControlInfo']['SpecialMemoryArrange'] = 'False'
      if caps & 0x1000 != 0:
        rsffile['AccessControlInfo']['CanAccessCore2'] = 'True'
      else:
        rsffile['AccessControlInfo']['CanAccessCore2'] = 'False'
    # MemoryMapping
    elif caps & 0xFFC00000 == 0xFF800000:
      if caps & 0x100000 != 0:  #read only
        rsffile['AccessControlInfo']['MemoryMapping']\
          .append("0x%0.1X%0.2X%0.2X000:r" % (caps >> 16 & 0xF, caps >> 8 & 0xFF, caps & 0xFF))
      else: #read write
        rsffile['AccessControlInfo']['MemoryMapping']\
          .append("0x%0.1X%0.2X%0.2X000" % (caps >> 16 & 0xF, caps >> 8 & 0xFF, caps & 0xFF))
    # IORegisterMapping
    elif caps & 0xFFF00000 == 0xFFE00000:
      rsffile['AccessControlInfo']['IORegisterMapping']\
        .append("0x%0.1X%0.2X%0.2X000" % (caps >> 16 & 0xF, caps >> 8 & 0xFF, caps & 0xFF))
    # Empty entry
    elif caps == 0xFFFFFFFF:
      pass
    else:
      warning("Unsupported ARM9 Kernel Capabilities Descriptor %0.8X!" % caps)

  # UseExtSaveData, EXtSaveDataId, UseOtherVariationSaveData, AccessibleSaveDataIds
  # makerom indicates a mask of 0xFFFFFF but only shifts 20 bits
  if accCtrlInfo['otherattrib'] & 0x2 != 0:
    ids = (accCtrlInfo['extdataid'] >>  0 & 0xFFFFF,
           accCtrlInfo['extdataid'] >> 20 & 0xFFFFF,
           accCtrlInfo['extdataid'] >> 40 & 0xFFFFF,
           accCtrlInfo['storageid'] >>  0 & 0xFFFFF,
           accCtrlInfo['storageid'] >> 20 & 0xFFFFF,
           accCtrlInfo['storageid'] >> 40 & 0xFFFFF)

    for id in ids:
      if id != 0x00000:
        rsffile['AccessControlInfo']['AccessibleSaveDataIds'].append(id)        
        
    del rsffile['AccessControlInfo']['OtherUserSaveDataId1']
    del rsffile['AccessControlInfo']['OtherUserSaveDataId2']
    del rsffile['AccessControlInfo']['OtherUserSaveDataId3']
  else:
    del rsffile['AccessControlInfo']['AccessibleSaveDataIds']

    if accCtrlInfo['extdataid'] != 0:
      rsffile['AccessControlInfo']['UseExtSaveData'] = 'True'
      rsffile['AccessControlInfo']['ExtSaveDataId'] = accCtrlInfo['extdataid']

    ids = (accCtrlInfo['storageid'] >>  0 & 0xFFFFF,
           accCtrlInfo['storageid'] >> 20 & 0xFFFFF,
           accCtrlInfo['storageid'] >> 40 & 0xFFFFF)
    if ids[0] != 0:
      rsffile['AccessControlInfo']['OtherUserSaveDataId1'] = ids[0]
    else:
      del rsffile['AccessControlInfo']['OtherUserSaveDataId1']
    if ids[1] != 0:
      rsffile['AccessControlInfo']['OtherUserSaveDataId2'] = ids[1]
    else:
      del rsffile['AccessControlInfo']['OtherUserSaveDataId2']
    if ids[2] != 0:
      rsffile['AccessControlInfo']['OtherUserSaveDataId3'] = ids[2]
    else:
      del rsffile['AccessControlInfo']['OtherUserSaveDataId3']

  if accCtrlInfo['storageid'] & 0x1000000000000000 != 0:
    rsffile['AccessControlInfo']['UseOtherVariationSaveData'] = 'True'
  else:
    rsffile['AccessControlInfo']['UseOtherVariationSaveData'] = 'False'
    
  # SystemSaveDataId(1,2)
  if accCtrlInfo['syssaveid1'] != 0:
    rsffile['AccessControlInfo']['SystemSaveDataId1'] = accCtrlInfo['syssaveid1']
  else:
    del rsffile['AccessControlInfo']['SystemSaveDataId1']
  if accCtrlInfo['syssaveid2'] != 0:
    rsffile['AccessControlInfo']['SystemSaveDataId2'] = accCtrlInfo['syssaveid2']
  else:
    del rsffile['AccessControlInfo']['SystemSaveDataId2']

  # EnableL2Cache, CpuSpeed
  if accCtrlInfo['flag1'] & 0x1 != 0:
    rsffile['AccessControlInfo']['EnableL2Cache'] = 'True'
  else:
    rsffile['AccessControlInfo']['EnableL2Cache'] = 'False'
  # this is just a flag, makerom will not accept other values for this
  if accCtrlInfo['flag1'] & 0x2 != 0:
    rsffile['AccessControlInfo']['CpuSpeed'] = '804mhz'
  else:
    rsffile['AccessControlInfo']['CpuSpeed'] = '268mhz'
  
  # IdealProcessor, AffinityMask, Priority, CoreVersion, DescVersion
  # ResourceLimtCategory, MaxCpu
  rsffile['AccessControlInfo']['IdealProcessor'] = accCtrlInfo['flag0'] >> 0 & 0x3
  rsffile['AccessControlInfo']['AffinityMask'] = accCtrlInfo['flag0'] >> 2 & 0x3
  rsffile['AccessControlInfo']['Priority'] = accCtrlInfo['priority'] - 32 # makerom increases this value by 32 for applications
  rsffile['AccessControlInfo']['CoreVersion'] = accCtrlInfo['corever']
  rsffile['AccessControlInfo']['DescVersion'] = accCtrlInfo['arm9ver']
  rsffile['AccessControlInfo']['ResourceLimitCategory'] = accCtrlInfo['category']
  rsffile['AccessControlInfo']['MaxCpu'] = accCtrlInfo['reslimits'][0]

  # SystemMode
  if accCtrlInfo['flag0'] >> 4 & 0xF == 0:
    rsffile['AccessControlInfo']['SystemMode'] = '64MB'
  elif accCtrlInfo['flag0'] >> 4 & 0xF == 1:
    rsffile['AccessControlInfo']['SystemMode'] = 'UNK'
  elif accCtrlInfo['flag0'] >> 4 & 0xF == 2:
    rsffile['AccessControlInfo']['SystemMode'] = '96MB'
  elif accCtrlInfo['flag0'] >> 4 & 0xF == 3:
    rsffile['AccessControlInfo']['SystemMode'] = '80MB'
  elif accCtrlInfo['flag0'] >> 4 & 0xF == 4:
    rsffile['AccessControlInfo']['SystemMode'] = '72MB'
  elif accCtrlInfo['flag0'] >> 4 & 0xF == 5:
    rsffile['AccessControlInfo']['SystemMode'] = '32MB'
  else:
    warning("Invalid SystemMode, ignoring!")
    del rsffile['AccessControlInfo']['SystemMode']
    
  # SystemModeExt
  # These are also just flags, they can't be set to any other value.
  if accCtrlInfo['flag2'] & 0x4 == 0:
    rsffile['AccessControlInfo']['SystemModeExt'] = 'Legacy'
  elif accCtrlInfo['flag2'] & 0x4 == 1:
    rsffile['AccessControlInfo']['SystemModeExt'] = '124MB'
  elif accCtrlInfo['flag2'] & 0x4 == 2:
    rsffile['AccessControlInfo']['SystemModeExt'] = '178MB'
  else:
    warning("Invalid SystemModeExt, ignoring!")
    del rsffile['AccessControlInfo']['SystemModeExt']
    
  # FileSystemAccess
  for fsPerm in enumerate(FSAccessInfo):
    if accCtrlInfo['fsaccess'] & (1 << fsPerm[0]) != 0:
      rsffile['AccessControlInfo']['FileSystemAccess'].append(fsPerm[1])

  # IoAccessControl
  for cap in enumerate(ARM9Access):
    if accCtrlInfo['arm9caps'] & (1 << cap[0]) != 0:
      rsffile['AccessControlInfo']['IoAccessControl'].append(cap[1])

  # ServiceAccessControl
  # These need to be converted to real strings later
  for service in accCtrlInfo['services']:
    if service != b'\x00\x00\x00\x00\x00\x00\x00\x00':
      rsffile['AccessControlInfo']['ServiceAccessControl'].append(service)


  # SystemControlInfo
  
  # StackSize, RemasterVersion, JumpId, SaveDataSize
  rsffile['SystemControlInfo']['StackSize'] = sysCtrlInfo['stack']
  rsffile['SystemControlInfo']['RemasterVersion'] = sysCtrlInfo['remaster']
  rsffile['SystemControlInfo']['JumpId'] = sysCtrlInfo['jumpid']
  rsffile['SystemControlInfo']['SaveDataSize'] = sysCtrlInfo['savesize'] # needs to be made "human readable" later

  # Dependency
  for dep in sysCtrlInfo['dependencies']:
    if dep != 0:
      rsffile['SystemControlInfo']['Dependency'].append(dep)


  # BasicInfo
  
  # Title, CompanyCode, ProductCode
  # These all need to be made in to proper strings
  rsffile['BasicInfo']['Title'] = sysCtrlInfo['title']
  rsffile['BasicInfo']['CompanyCode'] = ncchHdr['makercode']
  rsffile['BasicInfo']['ProductCode'] = ncchHdr['productcode']
  

  # TitleInfo
  
  # UniqueId
  rsffile['TitleInfo']['UniqueId'] = ncchHdr['programid'] >> 8 & 0xFFFFFF


def reformatData():
  # Reformat fields that need it
  for i in range(len(rsffile['AccessControlInfo']['InterruptNumbers'])):
    rsffile['AccessControlInfo']['InterruptNumbers'][i] =\
      "0x%0.2X" % rsffile['AccessControlInfo']['InterruptNumbers'][i]

  rsffile['AccessControlInfo']['HandleTableSize'] =\
    "0x%0.2X" % rsffile['AccessControlInfo']['HandleTableSize']
  
  # this is possibly removed
  if 'AccessibleSaveDataIds' in rsffile['AccessControlInfo']:
    for i in range(len(rsffile['AccessControlInfo']['AccessibleSaveDataIds'])):
      rsffile['AccessControlInfo']['AccessibleSaveDataIds'][i] =\
        "0x%0.6X" % rsffile['AccessControlInfo']['AccessibleSaveDataIds'][i]

  if 'ExtSaveDataId' in rsffile['AccessControlInfo']:
    rsffile['AccessControlInfo']['ExtSaveDataId'] =\
      "0x%0.16X" % rsffile['AccessControlInfo']['ExtSaveDataId']
  
  rsffile['AccessControlInfo']['CoreVersion'] =\
    "0x%X" % rsffile['AccessControlInfo']['CoreVersion']

  rsffile['AccessControlInfo']['DescVersion'] =\
    "0x%X" % rsffile['AccessControlInfo']['DescVersion']

  rsffile['AccessControlInfo']['ResourceLimitCategory'] =\
    "%0.2X" % rsffile['AccessControlInfo']['ResourceLimitCategory']

  rsffile['AccessControlInfo']['MaxCpu'] =\
    "0x%X" % rsffile['AccessControlInfo']['MaxCpu']

  if 'SystemSaveDataId1' in rsffile['AccessControlInfo']:
    rsffile['AccessControlInfo']['SystemSaveDataId1'] =\
      "0x%0.8X" % rsffile['AccessControlInfo']['SystemSaveDataId1']
  if 'SystemSaveDataId2' in rsffile['AccessControlInfo']:
    rsffile['AccessControlInfo']['SystemSaveDataId2'] =\
      "0x%0.8X" % rsffile['AccessControlInfo']['SystemSaveDataId2']
  if 'OtherUserSaveDataId1' in rsffile['AccessControlInfo']:
    rsffile['AccessControlInfo']['OtherUserSaveDataId1'] =\
      "0x%0.8X" % rsffile['AccessControlInfo']['OtherUserSaveDataId1']
  if 'OtherUserSaveDataId2' in rsffile['AccessControlInfo']:
    rsffile['AccessControlInfo']['OtherUserSaveDataId2'] =\
      "0x%0.8X" % rsffile['AccessControlInfo']['OtherUserSaveDataId2']
  if 'OtherUserSaveDataId3' in rsffile['AccessControlInfo']:
    rsffile['AccessControlInfo']['OtherUserSaveDataId3'] =\
      "0x%0.8X" % rsffile['AccessControlInfo']['OtherUserSaveDataId3']

  for i in range(len(rsffile['AccessControlInfo']['ServiceAccessControl'])):
    service = rsffile['AccessControlInfo']['ServiceAccessControl'][i]
    endchar = service.find(0x00)
    if endchar == -1:
      rsffile['AccessControlInfo']['ServiceAccessControl'][i] =\
        service.decode('ascii')
    else:
      rsffile['AccessControlInfo']['ServiceAccessControl'][i] =\
        service[:endchar].decode('ascii')

  rsffile['SystemControlInfo']['StackSize'] =\
    "0x%0.8X" % rsffile['SystemControlInfo']['StackSize']

  rsffile['SystemControlInfo']['RemasterVersion'] =\
    "%0.4X" % rsffile['SystemControlInfo']['RemasterVersion']

  rsffile['SystemControlInfo']['JumpId'] =\
    "0x%0.16X" % rsffile['SystemControlInfo']['JumpId']

  savesize = rsffile['SystemControlInfo']['SaveDataSize']
  if savesize >= GIGABYTE and (savesize % GIGABYTE) == 0:
    rsffile['SystemControlInfo']['SaveDataSize'] = "%dGB" % (savesize / GIGABYTE)
  elif savesize >= MEGABYTE and savesize < GIGABYTE and (savesize % MEGABYTE) == 0:
    rsffile['SystemControlInfo']['SaveDataSize'] = "%dMB" % (savesize / MEGABYTE)
  elif savesize >= KILOBYTE and savesize < MEGABYTE and (savesize % KILOBYTE) == 0:
    rsffile['SystemControlInfo']['SaveDataSize'] = "%dKB" % (savesize / KILOBYTE)
  else: # This probably doesn't work but it shouldn't ever come up
    rsffile['SystemControlInfo']['SaveDataSize'] = "%d" % savesize

  for i in range(len(rsffile['SystemControlInfo']['Dependency'])):
    rsffile['SystemControlInfo']['Dependency'][i] =\
      "asdf: 0x%0.16XL" % rsffile['SystemControlInfo']['Dependency'][i]

  title = rsffile['BasicInfo']['Title']
  endchar = title.find(0x00)
  if endchar == -1:
    rsffile['BasicInfo']['Title'] =\
      title.decode('ascii')
  else:
    rsffile['BasicInfo']['Title'] =\
      title[:endchar].decode('ascii')

  rsffile['BasicInfo']['CompanyCode'] =\
    rsffile['BasicInfo']['CompanyCode'].decode('ascii')

  pcode = rsffile['BasicInfo']['ProductCode']
  rsffile['BasicInfo']['ProductCode'] =\
    pcode[:pcode.find(b'\x00')].decode('ascii')

  rsffile['TitleInfo']['UniqueId'] =\
    "0x%0.6X" % rsffile['TitleInfo']['UniqueId']


def keyString(category, name):
  return("%s/%s" % (category, name))


def splitKeyValue(kv):
  equal = kv.index('=')
  if equal == 0 or equal == -1:
    raise ValueError
  return({'key': kv[:equal], 'value': kv[equal+1:]})


def splitKeyString(ks):
  slash = ks.find('/')
  if slash == 0 or slash + 1 == len(ks):
    raise ValueError
  if slash == -1:
    return({'category': ks})
  return({'category': ks[:slash], 'name': ks[slash+1:]})


def listTypes(listtypes):
  print(repr(specialLists))
  for item in listtypes:
    listtype = splitKeyValue(item)

    if listtype['value'] == 'nodash':
      if listtype['key'] in specialLists:
        raise ValueError("%s is already set to nodash" % listtype['key'])
      else:
        specialLists.append(listtype['key'])
    elif listtype['value'] == 'dash':
      if listtype['key'] not in specialLists:
        raise ValueError("%s is not set to nodash" % listtype['key'])
      else:
        specialLists.remove(listtype['key'])
    else:
      raise ValueError("List type must be 'dash' or 'nodash'")


def getListIndex(key):
  index = 0
  dot = key.find('.')
  
  if dot == -1:
    if key[len(key) - 1] == '+':
      return('add', key[:-1])
    elif key[len(key) - 1] == '-':
      return('clear', key[:-1])
    else:
      return(None, key)
  else:
    if dot == 0 or dot + 1 == len(key):
      raise ValueError
    index = int(key[dot+1:])
    if index < 0:
      raise ValueError("Negative list index %d" % index)
  
  return(index, key[:dot])


def delOptions(options):
  for option in options:
    kv = splitKeyString(option)

    if 'name' in kv:
      category = kv['category']
      index, name = getListIndex(kv['name'])
      
      if index == 'add':
        raise ValueError("'+' operator invalid for '--deloptions'")
      elif index == 'clear':
        if type(rsffile[category][name]) is list:
          rsffile[category][name] = list()
        else:
          raise ValueError("%s is not a list" % option)
      elif index == None:
        try:
          del rsffile[category][name]
        except KeyError as e:
          raise KeyError("%s doesn't exist" % option)
      else:
        del rsffile[category][name][index]
    else:
      try:
        del rsffile[kv['category']]
      except KeyError as e:
        raise KeyError("%s isn't a category" % option)


def addOptions(options):
  for option in options:
    kv = splitKeyValue(option)
    ks = splitKeyString(kv['key'])
    
    if 'name' in ks:
      category = ks['category']
      index, name = getListIndex(ks['name'])
      value = kv['value']
      
      if index == 'add':
        if category not in rsffile:
          rsffile[category] = dict()
        if name not in rsffile[category]:
          rsffile[category][name] = list()
        if type(rsffile[category][name]) is list:
          rsffile[category][name].append(value)
        else:
          raise KeyError("%s is not a list" % kv['key'])
      elif index == 'clear':
        raise KeyError("Can't use assingment with clear")
      elif index == None:
        if category not in rsffile:
          rsffile[category] = dict()
        elif name in rsffile[category] and type(rsffile[category][name]) is list:
          raise KeyError("Can't assign to list type, delete list first.")
        rsffile[category][name] = value
      else:
        if type(rsffile[category][name]) is not list:
          raise KeyError("Can't index non list type")
        else:
          rsffile[category][name][index] = value


# Not much safeguarding in this, but it's only a problem if you're noodling around
# Very VERY simple YAML printer
def writeRSF():
  for category in rsffile.keys():
    print("%s:" % (category))
    for item in rsffile[category].keys():
      if type(rsffile[category][item]) is str:
        print("  %s: %s" % (item, rsffile[category][item]))
      elif type(rsffile[category][item]) is int:
        print("  %s: %d" % (item, rsffile[category][item]))
      elif type(rsffile[category][item]) is list:
        print("  %s:" % (item))
        if keyString(category, item) in specialLists:
          for value in rsffile[category][item]:
            print("   %s" % (value))
        else:
          for value in rsffile[category][item]:
            print("  - %s" % (value))


parser = argparse.ArgumentParser(description="Generate RSF file from 3DS CCI " \
                                 "and exheader.")
parser.add_argument('rom', metavar="<CCI File>", type=str, help="ROM file to " \
                    "read data from.")
parser.add_argument('exheader', metavar="<ExHeader file>", type=str,
                    help="File containing the ExHeader.")
parser.add_argument('--romfsdir', metavar="<RomFs dir>", type=str,
                    help="Specify a RomFs path.")
parser.add_argument('--option', metavar="<Category/Name{,+,.#}=Value>",
                    type=str, action='append',
                    help="Set a custom value.  No checking for validity is " \
                    "done, so this will allow you to create unacceptable RSF " \
                    "files.  This can override existing values or add new " \
                    "ones.  New categories will also be added automatically. " \
                    "List values can be specified by adding a point '.' and " \
                    "a list index after the name.  You can also use the " \
                    "special value '+' instead of '.' to just append a " \
                    "value.  If you want to create a new list, you need to " \
                    "create it using the list append syntax.  Values will " \
                    "not be reformatted in any way and always written " \
                    "verbatim as given.")
parser.add_argument('--deloption', metavar="<Category/Name{,.#,-}>",
                    type=str, action='append',
                    help="Delete a category, item or list item.  Same naming " \
                    "conventions apply as '--option'.  '-' can be put after " \
                    "a name to clear a list.  '--deloption' happens before " \
                    "'--option'.")
parser.add_argument('--list-type', metavar="<Category/Name={nodash,dash}>",
                    type=str, action='append',
                    help="Makerom is kind of weird about certain kinds of " \
                    "lists where some need the items to begin with dashes " \
                    "('-'), and some need to be without.  This will Allow " \
                    "you to change how a list is output if you need to.")


args = parser.parse_args()
if args.list_type != None:
  listTypes(args.list_type)

with open(args.rom, 'rb') as f:
  ncsdHdr = makeNcsdHdrDictFromTuple(ncsdHdrStruct.unpack(f.read(ncsdHdrStruct.size)))
  f.seek(ncsdHdr['offsets'][0] * MEDIA_BLOCK_SIZE)
  ncchHdr = makeNcchHdrDictFromTuple(ncchHdrStruct.unpack(f.read(ncchHdrStruct.size)))

with open(args.exheader, 'rb') as f:
  sysCtrlInfo = makeSysCtrlInfoDictFromTuple(sysCtrlInfoStruct.unpack(f.read(sysCtrlInfoStruct.size)))
  accCtrlInfo = makeAccCtrlInfoDictFromTuple(accCtrlInfoStruct.unpack(f.read(accCtrlInfoStruct.size)))
  
populateRSFFile()
if args.romfsdir != None:
  rsffile['RomFs']['RootPath'] = args.romfsdir
else:
  del rsffile['RomFs']

reformatData()
if args.deloption != None:
  delOptions(args.deloption)
if args.option != None:
  addOptions(args.option)
writeRSF()
