#!/usr/bin/env python3
#
# qnxprobe - decide whether an extraction holds a QNX6 filesystem
# Copyright (c) 2026 Alexis Brignoni
# SPDX-License-Identifier: MIT
#
"""
Is this extraction QNX?

Every constant and every field offset below is read out of the Linux kernel's
own qnx6 driver, not assumed:

  QNX6_SUPER_MAGIC   0x68191122   include/uapi/linux/magic.h:55
  QNX6_BOOTBLOCK_SIZE    0x2000   include/linux/qnx6_fs.h:23
  QNX6_SUPERBLOCK_SIZE    0x200   include/linux/qnx6_fs.h:21
  struct qnx6_super_block          include/linux/qnx6_fs.h:94

fs/qnx6/inode.c reads the first superblock at QNX6_BOOTBLOCK_SIZE and, if the
magic is wrong there, retries at offset 0. It tries little endian first, then
big endian, so both are live in the wild.

A bare 4-byte magic match is NOT a finding: across a 256 MiB scan you expect
about one hit by chance. Each candidate is therefore parsed as a superblock and
its fields checked for internal consistency before it is reported CONFIRMED.

Read-only throughout. Never writes to the image.
"""
import os, re, struct, sys, datetime, json, time, uuid, zipfile

QNXPROBE_VERSION = "1.8"

QNX6_MAGIC     = 0x68191122
BOOTBLOCK_SIZE = 0x2000
SECTOR         = 512

MBR_QNX_TYPES = {   # util-linux include/pt-mbr-partnames.h v2.40
    0x4d: "QNX4.x", 0x4e: "QNX4.x 2nd part", 0x4f: "QNX4.x 3rd part",
}

# offsets into struct qnx6_super_block, in declaration order
F = dict(magic=0, checksum=4, serial=8, ctime=16, atime=20, flags=24,
         version1=28, version2=30, volumeid=32, blocksize=48,
         num_inodes=52, free_inodes=56, num_blocks=60, free_blocks=64,
         allocgroup=68)

# A filesystem created before QNX6 existed or far in the future is not real.
T_MIN = int(datetime.datetime(1995, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
T_MAX = int(datetime.datetime(2050, 1, 1, tzinfo=datetime.timezone.utc).timestamp())



def sb_slots(fh, base, label, sized_regions):
    """Every offset in this region that could hold a superblock copy.

    Measured on a Ford Sync G4 image: the 0x1000 area reserved for a superblock
    holds TWO 512-byte slots, 0xE00 apart, carrying the current and the previous
    committed generation. Documentation/filesystems/qnx6.rst puts one reserved
    area at 0x2000 (after the bootblock) and a second near the end of the
    filesystem, so both are probed. Yields (absolute offset, offset-in-region).
    """
    rels = [BOOTBLOCK_SIZE, BOOTBLOCK_SIZE + 0xE00, 0, 0xE00]

    # The trailing reserved area. Measured on a Ford Sync G4 image it sits at
    # (partition size - 0x1000), not at (num_blocks * blocksize - 0x1000), so
    # the declared partition size is tried first and the filesystem's own size
    # second.
    ends = []
    for rlabel, rbase, rsize in sized_regions:
        if rbase == base and rsize:
            ends.append(rsize)
    head = check(fh, base + BOOTBLOCK_SIZE) or check(fh, base)
    if head and not head[2]:
        total = head[1]["num_blocks"] * head[1]["blocksize"]
        if 0 < total < (1 << 42):
            ends.append(total)
    for e in ends:
        rels += [e - 0x1000, e - 0x200]

    seen = set()
    for rel in rels:
        if rel < 0 or rel in seen:
            continue
        seen.add(rel)
        yield base + rel, rel


def report_generations(copies, sized_regions, how_of):
    """copies: list of (off, how, endian, sb). Group by serial and diff."""
    gens = {}
    for off, how, endian, sb in copies:
        gens.setdefault(sb["serial"], {"sb": sb, "endian": endian, "at": []})
        gens[sb["serial"]]["at"].append(off)
    order = sorted(gens, reverse=True)
    return order, gens


def read_at(fh, off, n):
    try:
        fh.seek(off); return fh.read(n)
    except OSError:
        return b""


def ts(v):
    if not (T_MIN <= v <= T_MAX):
        return None
    return datetime.datetime.fromtimestamp(v, datetime.timezone.utc)


def duration(sec):
    """Largest two sensible units, e.g. '3 days 4 hours', '2 seconds'."""
    sec = abs(int(sec))
    if sec == 0:
        return "0 seconds"
    units = (("year", 31557600), ("day", 86400), ("hour", 3600),
             ("minute", 60), ("second", 1))
    parts, rem = [], sec
    for name, size in units:
        if rem >= size:
            n, rem = divmod(rem, size)
            parts.append(f"{n:,} {name}{'' if n == 1 else 's'}")
            if len(parts) == 2:
                break
    return " ".join(parts)


def delta_line(label, new, old):
    """One line describing how a stored time changed between two commits.

    A value outside the plausible range is an unset placeholder, not a date,
    so the difference against it is not a duration and is not reported as one.
    Measured on a Ford Sync G4 image: the previous generation of dps_os holds
    sb_atime 1, which naively differs from the active value by 54 years.
    """
    if new == old:
        return f"        {label:<12} unchanged"
    new_ok, old_ok = ts(new) is not None, ts(old) is not None
    if not old_ok and new_ok:
        return (f"        {label:<12} was unset (raw {old}), now "
                f"{ts(new):%Y-%m-%d %H:%M:%S} UTC   (not a duration)")
    if old_ok and not new_ok:
        return (f"        {label:<12} was {ts(old):%Y-%m-%d %H:%M:%S} UTC, "
                f"now unset (raw {new})   (not a duration)")
    if not new_ok and not old_ok:
        return f"        {label:<12} raw {old} -> raw {new}   (neither is a date)"
    d = new - old
    return (f"        {label:<12} {d:+,} s   ({'forward' if d > 0 else 'back'} "
            f"{duration(d)})")


def stamp(v):
    d = ts(v)
    return (f"{d:%Y-%m-%d %H:%M:%S} UTC" if d
            else f"raw {v}  (no valid clock when written)")


def parse_sb(buf, endian):
    """Parse a candidate superblock. Returns (dict, [reasons it failed])."""
    e = "<" if endian == "little endian" else ">"
    g32 = lambda k: struct.unpack_from(e + "I", buf, F[k])[0]
    g16 = lambda k: struct.unpack_from(e + "H", buf, F[k])[0]
    sb = dict(
        checksum=g32("checksum"),
        serial=struct.unpack_from(e + "Q", buf, F["serial"])[0],
        ctime=g32("ctime"), atime=g32("atime"), flags=g32("flags"),
        version1=g16("version1"), version2=g16("version2"),
        volumeid=buf[F["volumeid"]:F["volumeid"] + 16],
        blocksize=g32("blocksize"), num_inodes=g32("num_inodes"),
        free_inodes=g32("free_inodes"), num_blocks=g32("num_blocks"),
        free_blocks=g32("free_blocks"), allocgroup=g32("allocgroup"),
    )
    bad = []
    bs = sb["blocksize"]
    if not (512 <= bs <= 65536 and (bs & (bs - 1)) == 0):
        bad.append(f"blocksize {bs} not a power of two in 512..65536")
    # An embedded filesystem is often built on a host with no clock, so ctime
    # legitimately reads as a few seconds past the epoch. Measured on a Ford
    # Sync G4 dps_os partition: ctime 308, atime 2024-04-04, everything else
    # consistent and the volume size an exact match for its GPT entry.
    # Requiring BOTH timestamps rejected a real filesystem, so require one.
    if ts(sb["ctime"]) is None and ts(sb["atime"]) is None:
        bad.append(f"neither ctime ({sb['ctime']}) nor atime ({sb['atime']}) "
                   f"is a plausible date")
    if sb["free_blocks"] > sb["num_blocks"]:
        bad.append("free_blocks > num_blocks")
    if sb["free_inodes"] > sb["num_inodes"]:
        bad.append("free_inodes > num_inodes")
    if sb["num_blocks"] == 0:
        bad.append("num_blocks is zero")
    if sb["num_inodes"] == 0:
        bad.append("num_inodes is zero")
    return sb, bad


def check(fh, off):
    """Return (endian, sb, bad) if magic is at off, else None."""
    buf = read_at(fh, off, 512)
    if len(buf) < 512:
        return None
    for e, pk in (("little endian", "<I"), ("big endian", ">I")):
        if struct.unpack_from(pk, buf, 0)[0] == QNX6_MAGIC:
            sb, bad = parse_sb(buf, e)
            return e, sb, bad
    return None


def parse_mbr(fh):
    mbr = read_at(fh, 0, 512)
    if len(mbr) < 512 or mbr[510:512] != b"\x55\xaa":
        return None
    # A FAT or exFAT boot sector also ends in 0x55AA, and its boot code sits
    # where MBR partition entries would be, so it parses as four nonsense
    # partitions. Its own type string at bytes 3..11 (exFAT) or 82..90 (FAT32)
    # says it is a filesystem, not a partition table.
    if mbr[3:11] == b"EXFAT   " or mbr[82:90] == b"FAT32   " or mbr[54:62] == b"FAT16   ":
        return None
    out = []
    for i in range(4):
        ent = mbr[446 + i * 16: 446 + (i + 1) * 16]
        t = ent[4]
        start, cnt = struct.unpack("<II", ent[8:16])
        if t and cnt:
            out.append((i + 1, t, start, cnt))
    return out


def parse_gpt(fh):
    """Parse the GPT at LBA 1. Returns list of (idx, name, type_guid, start, end)."""
    hdr = read_at(fh, SECTOR, 92)
    if len(hdr) < 92 or hdr[0:8] != b"EFI PART":
        return None
    ent_lba, n_ent, ent_sz = struct.unpack_from("<QII", hdr, 72)
    out = []
    for i in range(min(n_ent, 256)):
        raw = read_at(fh, ent_lba * SECTOR + i * ent_sz, ent_sz)
        if len(raw) < 56:
            break
        tguid = raw[0:16]
        if tguid == b"\x00" * 16:
            continue
        first, last = struct.unpack_from("<QQ", raw, 32)
        name = raw[56:ent_sz].decode("utf-16-le", "replace").rstrip("\x00").strip()
        g = uuid.UUID(bytes_le=tguid)
        out.append((i + 1, name, str(g), first, last))
    return out


# ---------------------------------------------------------------------------
# What is actually in a partition, when it is not qnx6.
#
# A partition type byte is a label, not a fact. The BMW MGU image carries
# twelve partitions marked 0x83 "Linux"; ten hold ext4, one holds an ipk
# container with a Linux bzImage inside it, and one is the extended-partition
# container itself. So the type byte is reported, and then the bytes are read.
#
# ext offsets below were derived from struct ext4_super_block in the kernel's
# fs/ext4/ext4.h and cross-checked against that header's own /*NN*/ offset
# markers, all 15 of which agreed, with the struct totalling 1024 bytes.
# EXT2_SUPER_MAGIC 0xEF53 is from include/uapi/linux/magic.h:24.
# ---------------------------------------------------------------------------
EXT_SB_OFF   = 1024
EXT_MAGIC    = 0xEF53
EXT_F = dict(inodes_count=0, blocks_count=4, free_blocks=12, first_data_block=20,
             log_block_size=24, inodes_per_group=40, mtime=44, wtime=48,
             mnt_count=52, magic=56, state=58, lastcheck=64, inode_size=88,
             feature_compat=92, feature_incompat=96, uuid=104, volume_name=120,
             last_mounted=136, desc_size=254, mkfs_time=264, kbytes_written=376,
             error_count=404)
EXT_INCOMPAT_EXTENTS  = 0x0040   # ext4.h
EXT_COMPAT_HAS_JOURNAL = 0x0004  # ext4.h
EXT_VALID_FS = 0x0001            # ext4.h


def _e(sb, k, n=4):
    o = EXT_F[k]
    return int.from_bytes(sb[o:o + n], "little")


# ---------------------------------------------------------------------------
# Directory listing (--list)
#
# qnx6 block resolution follows fs/qnx6/inode.c qnx6_block_map():
#   ptrbits  = ilog2(blocksize / 4)                          inode.c:431
#   blks_off = (0x2000 >> bits) + (0x1000 >> bits)            inode.c:374
#   devblock = stored_block + blks_off                        inode.c:68
# Structure layouts are struct qnx6_inode_entry, qnx6_dir_entry,
# qnx6_long_dir_entry and qnx6_root_node in include/linux/qnx6_fs.h.
#
# ext4 layouts are struct ext4_super_block, ext4_group_desc, ext4_inode and
# ext4_dir_entry_2 in fs/ext4/ext4.h, plus the extent structures in
# fs/ext4/ext4_extents.h (EXT4_EXT_MAGIC 0xf30a).
# ---------------------------------------------------------------------------
QNX6_INODE_SIZE  = 0x80
QNX6_DIRENT_SIZE = 0x20
QNX6_ROOT_INO    = 1
QNX6_ROOTNODE    = dict(Inode=72, Longfile=232)   # offsets inside the superblock
S_IFDIR, S_IFLNK = 0o040000, 0o120000


def _fmt_time(v):
    """Per-file mtime. Unlike a superblock stamp, an epoch-era value here is
    ordinary on an embedded image (files staged before the clock was set), so
    it is shown rather than suppressed."""
    try:
        return datetime.datetime.fromtimestamp(
            v, datetime.timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return "-"


class Qnx6Walker:
    def __init__(self, fh, base, sb_off):
        self.fh, self.base = fh, base
        sb = read_at(fh, base + sb_off, 512)
        self.bs = struct.unpack_from("<I", sb, 48)[0]
        bits = self.bs.bit_length() - 1
        self.ptrbits = (self.bs // 4).bit_length() - 1
        self.blks_off = (0x2000 >> bits) + (0x1000 >> bits)
        self.inode_rn = self._rn(sb, QNX6_ROOTNODE["Inode"])
        self.long_rn = self._rn(sb, QNX6_ROOTNODE["Longfile"])

    @staticmethod
    def _rn(sb, o):
        return dict(ptr=list(struct.unpack_from("<16I", sb, o + 8)), levels=sb[o + 72])

    def _blk(self, b):
        return read_at(self.fh, self.base + b * self.bs, self.bs)

    def _map(self, ptrs, levels, n):
        bitdelta = self.ptrbits * levels
        mask = (1 << self.ptrbits) - 1
        lp = n >> bitdelta
        if lp > 15:
            return None
        blk = ptrs[lp] + self.blks_off
        for _ in range(levels):
            buf = self._blk(blk)
            if len(buf) < self.bs:
                return None
            bitdelta -= self.ptrbits
            ptr = struct.unpack_from("<I", buf, ((n >> bitdelta) & mask) * 4)[0]
            if ptr in (0, 0xFFFFFFFF):
                return None
            blk = ptr + self.blks_off
        return blk

    def _tree(self, rn, logical):
        b = self._map(rn["ptr"], rn["levels"], logical)
        return self._blk(b) if b is not None else None

    def inode(self, num):
        byte = (num - 1) * QNX6_INODE_SIZE
        buf = self._tree(self.inode_rn, byte // self.bs)
        if not buf:
            return None
        raw = buf[byte % self.bs:][:QNX6_INODE_SIZE]
        if len(raw) < QNX6_INODE_SIZE:
            return None
        return dict(size=struct.unpack_from("<Q", raw, 0)[0],
                    mtime=struct.unpack_from("<I", raw, 20)[0],
                    mode=struct.unpack_from("<H", raw, 32)[0],
                    ptr=list(struct.unpack_from("<16I", raw, 36)),
                    levels=raw[100])

    def _longname(self, blk):
        buf = self._tree(self.long_rn, blk)
        if not buf:
            return "<longname unreadable>"
        n = struct.unpack_from("<H", buf, 0)[0]
        return buf[2:2 + min(n, 510)].decode("utf-8", "replace")

    def listdir(self, num):
        ino = self.inode(num)
        if not ino or not (ino["mode"] & S_IFDIR):
            return []
        out = []
        for lb in range((ino["size"] + self.bs - 1) // self.bs):
            b = self._map(ino["ptr"], ino["levels"], lb)
            if b is None:
                continue
            buf = self._blk(b)
            for p in range(0, len(buf) - QNX6_DIRENT_SIZE + 1, QNX6_DIRENT_SIZE):
                de_ino = struct.unpack_from("<I", buf, p)[0]
                de_size = buf[p + 4]
                if not de_ino or not de_size:
                    continue
                if de_size == 0xFF:
                    name = self._longname(struct.unpack_from("<I", buf, p + 8)[0])
                else:
                    name = buf[p + 5:p + 5 + min(de_size, 27)].decode("utf-8", "replace")
                if name not in (".", ".."):
                    out.append((name, de_ino))
        return sorted(out)

    def entry(self, num):
        ino = self.inode(num)
        if not ino:
            return None
        return ino["mode"], ino["size"], ino["mtime"]

    def read_file(self, num, size):
        """Yield the file's bytes a block at a time. An unmapped block is a
        hole and is emitted as zeros, so offsets stay correct."""
        ino = self.inode(num)
        if not ino:
            return
        left = size
        for lb in range((size + self.bs - 1) // self.bs):
            b = self._map(ino["ptr"], ino["levels"], lb)
            buf = self._blk(b) if b is not None else bytes(self.bs)
            if len(buf) < self.bs:
                buf = buf + bytes(self.bs - len(buf))
            take = min(self.bs, left)
            yield buf[:take]
            left -= take
            if left <= 0:
                return

    root = QNX6_ROOT_INO


class ExtWalker:
    def __init__(self, fh, base):
        self.fh, self.base = fh, base
        sb = read_at(fh, base + EXT_SB_OFF, 1024)
        self.bs = 1024 << _e(sb, "log_block_size")
        self.ipg = _e(sb, "inodes_per_group")
        self.fdb = _e(sb, "first_data_block")
        self.isz = _e(sb, "inode_size", 2)
        is64 = bool(_e(sb, "feature_incompat") & 0x80)
        self.dsz = _e(sb, "desc_size", 2) if is64 else 32
        self.is64 = is64

    def _blk(self, b):
        return read_at(self.fh, self.base + b * self.bs, self.bs)

    def inode(self, num):
        g, idx = divmod(num - 1, self.ipg)
        gd = read_at(self.fh, self.base + (self.fdb + 1) * self.bs + g * self.dsz, self.dsz)
        if len(gd) < 12:
            return None
        it = int.from_bytes(gd[8:12], "little")
        if self.is64 and self.dsz >= 44:
            it |= int.from_bytes(gd[40:44], "little") << 32
        raw = read_at(self.fh, self.base + it * self.bs + idx * self.isz, self.isz)
        if len(raw) < 60:
            return None
        return raw

    def _blocks(self, raw):
        if not (int.from_bytes(raw[32:36], "little") & 0x80000):
            return []                                   # not extent-mapped
        def walk(buf, off):
            if struct.unpack_from("<H", buf, off)[0] != 0xF30A:
                return []
            ent = struct.unpack_from("<H", buf, off + 2)[0]
            depth = struct.unpack_from("<H", buf, off + 6)[0]
            out = []
            for i in range(ent):
                o = off + 12 + i * 12
                if depth == 0:
                    st = (struct.unpack_from("<I", buf, o + 8)[0]
                          | struct.unpack_from("<H", buf, o + 6)[0] << 32)
                    ln = struct.unpack_from("<H", buf, o + 4)[0] & 0x7FFF
                    out += list(range(st, st + ln))
                else:
                    leaf = (struct.unpack_from("<I", buf, o + 4)[0]
                            | struct.unpack_from("<H", buf, o + 8)[0] << 32)
                    out += walk(self._blk(leaf), 0)
            return out
        return walk(raw, 40)

    def listdir(self, num):
        raw = self.inode(num)
        if not raw:
            return []
        out = []
        for b in self._blocks(raw):
            buf = self._blk(b)
            p = 0
            while p < len(buf) - 8:
                i = struct.unpack_from("<I", buf, p)[0]
                rec = struct.unpack_from("<H", buf, p + 4)[0]
                nl = buf[p + 6]
                if rec < 8 or p + rec > len(buf):
                    break
                if i and nl:
                    nm = buf[p + 8:p + 8 + nl].decode("utf-8", "replace")
                    if nm not in (".", ".."):
                        out.append((nm, i))
                p += rec
        return sorted(out)

    def entry(self, num):
        raw = self.inode(num)
        if not raw:
            return None
        mode = struct.unpack_from("<H", raw, 0)[0]
        size = (struct.unpack_from("<I", raw, 4)[0]
                | struct.unpack_from("<I", raw, 108)[0] << 32)
        return mode, size, struct.unpack_from("<I", raw, 16)[0]

    def read_file(self, num, size):
        raw = self.inode(num)
        if not raw:
            return
        left = size
        for b in self._blocks(raw):
            if left <= 0:
                return
            buf = self._blk(b)
            if len(buf) < self.bs:
                buf = buf + bytes(self.bs - len(buf))
            take = min(self.bs, left)
            yield buf[:take]
            left -= take

    root = 2


# ---------------------------------------------------------------------------
# FAT32 and exFAT.
#
# FAT is the file system of removable media and of many embedded devices, so a
# vehicle image can carry one beside its QNX and ext volumes. Both are read
# here directly, no mounting.
#
# Field offsets are from Microsoft's own specifications: the FAT32 BPB from the
# "Microsoft Extensible Firmware Initiative FAT32 File System Specification"
# v1.03, and the exFAT structures from the "exFAT file system specification"
# (Microsoft, 2019). Long file names on FAT are the VFAT scheme (UTF-16 across
# 0x0F entries); exFAT names are UTF-16 in a chain of file-name directory
# entries. Only the fields needed to list and read files are parsed.
# ---------------------------------------------------------------------------

class Fat32Walker:
    """List and read files from a FAT32 volume. inode() takes a (cluster, size,
    is_dir) tuple, so the shared collect()/extract_to_zip() work unchanged; the
    root is that tuple for the root cluster."""

    def __init__(self, fh, base):
        self.fh = fh
        self.base = base
        bpb = read_at(fh, base, 512)
        self.bps = struct.unpack_from("<H", bpb, 11)[0]
        self.spc = bpb[13]
        self.reserved = struct.unpack_from("<H", bpb, 14)[0]
        self.nfats = bpb[16]
        self.spf = struct.unpack_from("<I", bpb, 36)[0]
        self.root_clus = struct.unpack_from("<I", bpb, 44)[0]
        self.fat_start = base + self.reserved * self.bps
        self.data_start = self.fat_start + self.nfats * self.spf * self.bps
        self.cluster_bytes = self.spc * self.bps
        self.root = (self.root_clus, 0, True)

    def _fat_next(self, clus):
        off = self.fat_start + clus * 4
        val = struct.unpack_from("<I", read_at(self.fh, off, 4), 0)[0] & 0x0FFFFFFF
        return val

    def _chain(self, clus):
        seen = set()
        while 0x2 <= clus < 0x0FFFFFF8 and clus not in seen:
            seen.add(clus)
            yield clus
            clus = self._fat_next(clus)

    def _cluster_off(self, clus):
        return self.data_start + (clus - 2) * self.cluster_bytes

    def _read_chain(self, clus, size=None):
        out = bytearray()
        for c in self._chain(clus):
            out += read_at(self.fh, self._cluster_off(c), self.cluster_bytes)
            if size is not None and len(out) >= size:
                break
        return bytes(out[:size]) if size is not None else bytes(out)

    def inode(self, node):
        return node    # (cluster, size, is_dir) already carries what entry() needs

    def entry(self, node):
        clus, size, is_dir = node
        mode = 0o040000 if is_dir else 0o100000
        return (mode, size, 0)

    def listdir(self, node):
        clus = node[0]
        raw = self._read_chain(clus)
        out, lfn = [], []
        for i in range(0, len(raw), 32):
            e = raw[i:i + 32]
            if len(e) < 32 or e[0] == 0x00:
                break
            if e[0] == 0xE5:
                lfn = []; continue
            attr = e[11]
            if attr == 0x0F:                       # VFAT long-name fragment
                seq = e[0] & 0x3F
                chars = e[1:11] + e[14:26] + e[28:32]
                lfn.append((seq, chars)); continue
            if attr & 0x08:                        # volume label
                lfn = []; continue
            name = _vfat_name(lfn) if lfn else _fat_short_name(e)
            lfn = []
            hi = struct.unpack_from("<H", e, 20)[0]
            lo = struct.unpack_from("<H", e, 26)[0]
            first = (hi << 16) | lo
            sz = struct.unpack_from("<I", e, 28)[0]
            is_sub = bool(attr & 0x10)
            if name in (".", ".."):
                continue
            out.append((name, (first or 2, sz, is_sub)))
        return out

    def read_file(self, node, size):
        clus, sz, _ = node
        yield self._read_chain(clus, sz)


def _fat_short_name(e):
    # Byte 12 carries Windows NT's case flags for a short name that had no long
    # entry: 0x08 lowercases the base, 0x10 the extension. Honouring them keeps
    # the recorded case of an 8.3 name, which a filename in evidence should hold.
    nt = e[12]
    base = e[0:8].decode("ascii", "replace").rstrip(" ")
    ext = e[8:11].decode("ascii", "replace").rstrip(" ")
    if nt & 0x08:
        base = base.lower()
    if nt & 0x10:
        ext = ext.lower()
    return f"{base}.{ext}" if ext else base


def _vfat_name(lfn):
    parts = sorted(lfn, key=lambda x: x[0])
    raw = b"".join(chunk for _, chunk in parts)
    name = raw.decode("utf-16-le", "replace")
    end = name.find("\uffff")
    if end != -1:
        name = name[:end]
    return name.split("\x00")[0]


class ExfatWalker:
    """List and read files from an exFAT volume, same interface as Fat32Walker.
    A node is (cluster, size, is_dir, fat_chain_flag)."""

    def __init__(self, fh, base):
        self.fh = fh
        self.base = base
        b = read_at(fh, base, 512)
        self.bps = 1 << b[108]
        self.spc = 1 << b[109]
        self.fat_off = struct.unpack_from("<I", b, 80)[0]
        self.heap_off = struct.unpack_from("<I", b, 88)[0]
        self.root_clus = struct.unpack_from("<I", b, 96)[0]
        self.cluster_bytes = self.bps * self.spc
        self.fat_start = base + self.fat_off * self.bps
        self.heap_start = base + self.heap_off * self.bps
        self.root = (self.root_clus, 0, True, False)

    def _fat_next(self, clus):
        v = struct.unpack_from("<I", read_at(self.fh, self.fat_start + clus * 4, 4), 0)[0]
        return v

    def _cluster_off(self, clus):
        return self.heap_start + (clus - 2) * self.cluster_bytes

    def _read(self, clus, size, contiguous):
        out = bytearray()
        if contiguous:
            need = size if size else self.cluster_bytes
            n = (need + self.cluster_bytes - 1) // self.cluster_bytes
            for i in range(n):
                out += read_at(self.fh, self._cluster_off(clus + i), self.cluster_bytes)
        else:
            seen = set()
            c = clus
            while 0x2 <= c < 0xFFFFFFF7 and c not in seen:
                seen.add(c)
                out += read_at(self.fh, self._cluster_off(c), self.cluster_bytes)
                if size and len(out) >= size:
                    break
                c = self._fat_next(c)
        return bytes(out[:size]) if size else bytes(out)

    def inode(self, node):
        return node

    def entry(self, node):
        _, size, is_dir, _ = node
        return (0o040000 if is_dir else 0o100000, size, 0)

    def listdir(self, node):
        clus, _, _, contig = node
        raw = self._read(clus, 0, contig)
        out = []
        i = 0
        while i < len(raw):
            etype = raw[i]
            if etype == 0x00:
                break
            if etype == 0x85:                       # File directory entry
                secs = raw[i + 1]
                s2 = raw[i + 32:i + 64]             # Stream extension (next entry)
                flags = s2[1]
                name_len = s2[3]
                first = struct.unpack_from("<I", s2, 20)[0]
                data_len = struct.unpack_from("<Q", s2, 24)[0]
                is_dir = bool(raw[i + 4] & 0x10)
                contiguous = bool(flags & 0x02)
                # name entries follow, 0xC1, 15 UTF-16 chars each
                name = ""
                for k in range(2, secs + 1):
                    ent = raw[i + 32 * k:i + 32 * k + 32]
                    if not ent or ent[0] != 0xC1:
                        break
                    name += ent[2:32].decode("utf-16-le", "replace")
                name = name[:name_len]
                if name not in (".", ".."):
                    out.append((name, (first, data_len, is_dir, contiguous)))
                i += 32 * (secs + 1)
            else:
                i += 32
        return out

    def read_file(self, node, size):
        clus, sz, _, contig = node
        yield self._read(clus, sz, contig)


# ---------------------------------------------------------------------------
# QNX flash filesystems: ETFS and EFS.
#
# These are QNX's two on-flash filesystems, the kind a head unit stores its
# manufacturing and configuration data on. QNX does not publish either byte
# layout. Both structures below are transcribed from the Kaitai .ksy specs in
# NetherlandsForensicInstitute/qnxmount (Apache-2.0), a peer institute's
# vehicle-forensics reader. Its ETFS spec cross-references QNX's own fs/etfs.h
# and its EFS spec fs/f3s_spec.h, the same way the qnx6 code above is sourced
# to the Linux driver. The Kaitai runtime is NOT taken as a dependency; only
# the field layouts are transcribed, into the same hand-written struct style,
# so this stays standard library only.
#
# Validated by round-trip against qnxmount's own committed test images: every
# file name, mode, owner, mtime, symlink target and byte of file content
# matched the tar archive built from the same live filesystem, ETFS 32 of 32
# entries and EFS 31 of 31. The tar archives were produced by qnxmount's build
# scripts on QNX, an implementation independent of this one.
#
# Both are typically imaged bare, with no partition table, so they arrive as
# the whole-image region and are read at base 0.
#
# ETFS is transaction based. The flash is a run of fixed-size pages, each
# holding <pagesize> bytes of user data followed by a 16-byte transaction
# record, which on real NAND lives in the spare/out-of-band area:
#     fid u4, cluster u4, nclusters u2, tacode u1, dacode u1, sequence u4
# The live state is rebuilt by keeping, for every (fid, cluster), the record
# with the highest sequence number, and ignoring pages whose transaction code
# is not "ok" or "ecc" (erased and 0xFF-filler pages carry a junk cluster).
# Files are addressed by a fixed file-id scheme from fs/etfs.h: root 0,
# .filetable 1, .badblks 2, .counts 3, .lost+found 4, .reserved 5, first real
# file 6. The .filetable (fid 1) is itself a file whose data is 64-byte entries
# indexed by fid, each carrying a file's parent id, mode, owner, times, size
# and short name; a name longer than 32 bytes is continued in an extension
# entry the short entry points at.
# Source: qnxmount/etfs/parser.ksy and qnxmount/etfs/interface.py, fs/etfs.h.
# ---------------------------------------------------------------------------
ETFS_TRANS_SIZE = 16
ETFS_ENTRY_SIZE = 64
ETFS_FID_ROOT, ETFS_FID_FTABLE = 0, 1
ETFS_RESERVED = {1: ".filetable", 2: ".badblks", 3: ".counts",
                 4: ".lost+found", 5: ".reserved"}
ETFS_PAGE_SIZES = (512, 1024, 2048, 4096, 8192, 16384)


def _etfs_scan_transactions(fh, base, pagesize, n, want_fid=None, cap=None):
    """Yield (page_index, fid, cluster, tacode, sequence) for pages whose
    transaction code is ok or ecc. Reads in blocks to avoid a syscall per page.
    Stops after cap pages if given, and filters to want_fid if given."""
    unit = pagesize + ETFS_TRANS_SIZE
    limit = n if cap is None else min(n, cap)
    BLK = 4096
    start = 0
    while start < limit:
        count = min(BLK, limit - start)
        buf = read_at(fh, base + start * unit, count * unit)
        if len(buf) < count * unit:
            count = len(buf) // unit
        for k in range(count):
            t = buf[k * unit + pagesize: k * unit + unit]
            if len(t) < ETFS_TRANS_SIZE:
                break
            fid, cluster = struct.unpack_from("<II", t, 0)
            if fid == 0xFFFFFFFF:
                continue
            if (t[10] & 0x0F) not in (0, 1):     # keep only ok / ecc pages
                continue
            if want_fid is not None and fid != want_fid:
                continue
            seq = struct.unpack_from("<I", t, 12)[0]
            yield start + k, fid, cluster, t[10], seq
        start += count
        if count == 0:
            break


def _etfs_parse_entry(raw):
    """One 64-byte .filetable entry, or None."""
    if len(raw) < ETFS_ENTRY_SIZE:
        return None
    efid, pfid = struct.unpack_from("<HH", raw, 0)
    is_ext = efid == 0x8000
    no_parent = pfid == 0xFFFF
    etype = int(is_ext) + int(no_parent) * 2
    e = dict(efid=efid, pfid=pfid, is_ext=is_ext, is_solo=efid == 0x0000,
             is_valid=efid != 0xFFFF, body=None, full=None)
    if etype == 0:                                # file entry
        mode, uid, gid, atime, mtime, ctime, size = struct.unpack_from("<7I", raw, 4)
        name = raw[32:64].split(b"\x00", 1)[0].decode("utf-8", "replace")
        e["body"] = dict(mode=mode, uid=uid, gid=gid, mtime=mtime,
                         ctime=ctime, size=size, name=name)
    elif etype == 1:                              # extension-name entry
        e["body"] = dict(name=raw[4:63].split(b"\x00", 1)[0].decode("utf-8", "replace"))
    return e


class EtfsWalker:
    """Reconstruct an ETFS filesystem by replaying its transactions, then walk
    it through the shared collect()/extract interface. A node is a file id."""

    root = ETFS_FID_ROOT

    def __init__(self, fh, base, size, pagesize):
        self.fh, self.base, self.bs = fh, base, pagesize
        self.unit = pagesize + ETFS_TRANS_SIZE
        self.n = size // self.unit
        # current page for every (fid, cluster): the highest sequence wins, and
        # for equal sequences the later physical page, matching qnxmount.
        cur = {}
        for pi, fid, cluster, ta, seq in _etfs_scan_transactions(fh, base, pagesize, self.n):
            d = cur.setdefault(fid, {})
            if cluster not in d or seq >= d[cluster][0]:
                d[cluster] = (seq, pi)
        self.cur = cur
        self.ftable = self._build_ftable()
        self._resolve_names()
        self.kids = self._build_children()

    def _page_data(self, page_index):
        return read_at(self.fh, self.base + page_index * self.unit, self.bs)

    def _build_ftable(self):
        per = self.bs // ETFS_ENTRY_SIZE
        pages = self.cur.get(ETFS_FID_FTABLE, {})
        if not pages:
            return []
        ftable = []
        for cluster in range(max(pages) + 1):
            if cluster not in pages:
                ftable.extend([None] * per)
                continue
            data = self._page_data(pages[cluster][1])
            for k in range(per):
                ftable.append(_etfs_parse_entry(data[k * ETFS_ENTRY_SIZE:
                                                     (k + 1) * ETFS_ENTRY_SIZE]))
        return ftable

    def _resolve_names(self):
        ft = self.ftable
        for e in ft:
            if e is None or e["body"] is None:
                continue
            if e["is_ext"] or not e["is_valid"]:
                e["full"] = None
            elif e["is_solo"]:
                e["full"] = e["body"]["name"]
            else:
                ext = ft[e["efid"]] if e["efid"] < len(ft) else None
                if ext is not None and ext["is_ext"] and ext["body"]:
                    e["full"] = e["body"]["name"] + ext["body"]["name"]
                else:
                    e["full"] = e["body"]["name"]

    def _build_children(self):
        """parent fid -> [(name, fid)]. An entry whose parent id no longer
        resolves to a real named entry (its page was lost, or the slot is
        unallocated) is an orphan; qnxmount routes those to /recovered_files, so
        they are attached to the root under that name rather than dropped."""
        kids = {}
        ft = self.ftable
        self.orphans = []
        for fid, e in enumerate(ft):
            if fid == ETFS_FID_ROOT or e is None or e["full"] is None:
                continue
            pf = e["pfid"]
            parent_ok = (0 <= pf < len(ft) and ft[pf] is not None
                         and ft[pf]["full"] is not None)
            if parent_ok:
                kids.setdefault(pf, []).append((e["full"], fid))
            else:
                self.orphans.append((e["full"], fid))
        return kids

    def listdir(self, fid):
        if fid == -1:                             # synthetic recovered_files dir
            return sorted(self.orphans)
        out = list(self.kids.get(fid, []))
        if fid == ETFS_FID_ROOT and self.orphans:
            out.append(("recovered_files", -1))
        return sorted(out)

    def entry(self, fid):
        if fid == -1:                             # synthetic recovered_files dir
            return (S_IFDIR | 0o755, 0, 0)
        e = self.ftable[fid] if 0 <= fid < len(self.ftable) else None
        if e is None or e["body"] is None:
            return None
        b = e["body"]
        return (b["mode"], b["size"], b["mtime"])

    def read_file(self, fid, size):
        if fid == -1:
            return
        pages = self.cur.get(fid, {})
        left = size
        if not pages:
            return
        for cluster in range(max(pages) + 1):
            if left <= 0:
                return
            if cluster in pages:
                buf = self._page_data(pages[cluster][1])
            else:
                buf = b"\xff" * self.bs           # a hole reads as 0xFF on flash
            if len(buf) < self.bs:
                buf = buf + bytes(self.bs - len(buf))
            take = min(self.bs, left)
            yield buf[:take]
            left -= take


# ---------------------------------------------------------------------------
# EFS is QNX's other flash filesystem, the F3S "flash 3" format. It is not
# transaction based: the flash is divided into erase units, each unit carries a
# growing-downward array of 32-byte extent headers at its end and the extent
# data (text) packed from the front. An extent header names the data's offset
# and size, a "next" pointer chaining the extents of one object, and a "super"
# pointer to a newer version that supersedes it, which is how EFS does its
# copy-on-write. Physical units are mapped to logical numbers through a per-unit
# logi record, so a pointer is (logical unit, extent index).
#
# A directory's first extent points at its first child; each child extent's
# "next" chains to the following sibling, and each child's own "first" descends
# into it. A file's extents chained by "next" are its data. The partition is
# found by its boot record, an extent whose text begins with the ASCII
# signature "QSSL_F3S"; the unit size is read from the unit_info at the start of
# the first unit. Source: qnxmount/efs/parser.ksy and interface.py, fs/f3s_spec.h.
# ---------------------------------------------------------------------------
EFS_SIG = b"QSSL_F3S"
EFS_EXTHDR = 32


def _efs_boot(fh, base, scan_bytes):
    """Find the QSSL_F3S boot record in the first scan_bytes of the region and
    return its parsed boot_info, or None. The boot_info starts 4 bytes before
    the signature (struct_size u2, rev_major u1, rev_minor u1, then the sig)."""
    chunk = read_at(fh, base, scan_bytes)
    at = chunk.find(EFS_SIG)
    if at < 4:
        return None
    o = at - 4
    struct_size = struct.unpack_from("<H", chunk, o)[0]
    rev_major, rev_minor = chunk[o + 2], chunk[o + 3]
    if struct_size != 0x18 or rev_major != 3 or rev_minor != 0:
        return None
    unit_index, unit_total, unit_spare, align_pow2 = struct.unpack_from("<HHHH", chunk, o + 12)
    root = struct.unpack_from("<HH", chunk, o + 20)
    return dict(unit_index=unit_index, unit_total=unit_total, unit_spare=unit_spare,
                align_pow2=align_pow2, root=root, sig_at=at)


def _efs_unit_size(fh, base):
    """The unit size from the unit_info at the start of the first unit. reserve
    bytes must read 0xFF for this to be a plausible EFS unit header."""
    b = read_at(fh, base, 16)
    if len(b) < 16 or b[3] != 0xFF or b[6:8] != b"\xff\xff":
        return None
    unit_pow2 = struct.unpack_from("<H", b, 4)[0]
    if not (9 <= unit_pow2 <= 30):
        return None
    return 1 << unit_pow2


class EfsWalker:
    """Reconstruct an EFS (F3S) filesystem and walk it through the shared
    interface. A node is a parsed directory entry (a dict)."""

    def __init__(self, fh, base):
        self.fh, self.base = fh, base
        self.unit_size = _efs_unit_size(fh, base)
        boot = _efs_boot(fh, base, min(self.unit_size * 4, 1 << 24))
        self.boot = boot
        self.align = boot["align_pow2"]
        self.units = [read_at(fh, base + u * self.unit_size, self.unit_size)
                      for u in range(boot["unit_total"])]
        self.logi_map = self._logi_map()
        self.root = self._as_node(self._get_ext(boot["root"]))[1]

    def _ext_header(self, unit, i):
        off = self.unit_size - EFS_EXTHDR * (i + 1)
        if off < 0 or off + EFS_EXTHDR > len(unit):
            return None
        h = unit[off:off + EFS_EXTHDR]
        s0 = struct.unpack_from("<I", h, 0)[0]
        return dict(no_next=bool((s0 >> 1) & 1), no_super=bool((s0 >> 2) & 1),
                    ext_last=bool((s0 >> 7) & 1), type=(s0 >> 8) & 3,
                    status1=struct.unpack_from("<I", h, 4)[0],
                    toff_hi=h[19], toff_lo=struct.unpack_from("<H", h, 20)[0],
                    tsize=struct.unpack_from("<H", h, 22)[0],
                    next=struct.unpack_from("<HH", h, 24),
                    super=struct.unpack_from("<HH", h, 28))

    def _extents(self, unit):
        exts, i = [], 0
        while True:
            h = self._ext_header(unit, i)
            if h is None:
                break
            exts.append(h)
            if h["ext_last"] or i > 4096:
                break
            i += 1
        return exts

    def _text(self, unit, hdr):
        off = ((hdr["toff_hi"] << 16) + hdr["toff_lo"]) << self.align
        return unit[off:off + hdr["tsize"]]

    @staticmethod
    def _is_spare(exts):
        return (len(exts) == 1
                or (len(exts) == 2 and exts[1]["status1"] == 0xFFFFFFFF))

    def _logi_map(self):
        logi = {}
        for unit in self.units:
            exts = self._extents(unit)
            if len(exts) < 2 or self._is_spare(exts):   # no logi record to read
                continue
            t = self._text(unit, exts[1])            # unit_logi: struct_size, logi
            logi[struct.unpack_from("<H", t, 2)[0]] = (unit, exts)
        return logi

    def _get_ext(self, ptr):
        unit, exts = self.logi_map[ptr[0]]
        hdr = exts[ptr[1]]
        while not hdr["no_super"]:                   # follow to the current version
            ptr = hdr["super"]
            unit, exts = self.logi_map[ptr[0]]
            hdr = exts[ptr[1]]
        return unit, hdr

    def _as_node(self, ext):
        """A directory entry, as the hashable node (first_logi, first_index,
        mode, mtime) the shared walker interface passes around. It stays hashable
        so collect()'s cycle-guard set can hold it; first uniquely identifies the
        object, so it doubles as identity. The name is returned by listdir, not
        carried in the node."""
        unit, hdr = ext
        t = self._text(unit, hdr)
        namelen = t[3]
        first = struct.unpack_from("<HH", t, 4)
        name = t[8:8 + namelen].split(b"\x00", 1)[0].decode("utf-8", "replace")
        so = 8 + ((namelen + 3) & 0xFC)              # name+pad is 4-byte aligned
        mode = struct.unpack_from("<H", t, so + 2)[0]
        mtime = struct.unpack_from("<I", t, so + 12)[0]
        return name, (first[0], first[1], mode, mtime)

    def _chain(self, node):
        first = (node[0], node[1])
        unit, hdr = self._get_ext(first)
        yield unit, hdr
        while not hdr["no_next"]:
            unit, hdr = self._get_ext(hdr["next"])
            yield unit, hdr

    def listdir(self, node):
        out = []
        for unit, hdr in self._chain(node):
            if not hdr["tsize"]:
                break
            out.append(self._as_node((unit, hdr)))
        return out

    def _size(self, node):
        return sum(hdr["tsize"] for _, hdr in self._chain(node))

    def entry(self, node):
        mode = node[2]
        size = self._size(node) if (mode & 0o170000) in (0o100000, 0o120000) else 0
        return (mode, size, node[3])

    def read_file(self, node, size):
        out = bytearray()
        for unit, hdr in self._chain(node):
            out += self._text(unit, hdr)
        yield bytes(out[:size]) if size else bytes(out)


def print_tree(w, num, depth, maxdepth, budget, indent=0, pad=6):
    for name, ino in w.listdir(num):
        if budget[0] <= 0:
            print(f"{' '*pad}{'  '*indent}... listing truncated, raise --list-max")
            return
        budget[0] -= 1
        ent = w.entry(ino)
        if not ent:
            continue
        mode, size, mtime = ent
        isdir = bool(mode & S_IFDIR)
        kind = "dir " if isdir else ("link" if mode & S_IFLNK == S_IFLNK else "file")
        col = max(12, 44 - 2 * indent)
        shown = "" if isdir else f"{human(size):>11}"
        print(f"{' '*pad}{'  '*indent}{kind} {name:<{col}} {shown}  {_fmt_time(mtime)}")
        if isdir and depth < maxdepth:
            print_tree(w, ino, depth + 1, maxdepth, budget, indent + 1, pad)


# ---------------------------------------------------------------------------
# QNX IFS boot images.
#
# An IFS is not a mountable filesystem, it is a bootable image: a startup
# header, the startup code, then the image filesystem, usually compressed.
# Constants and field order from sys/startup.h:
#     STARTUP_HDR_SIGNATURE 0x00ff7eeb   startup.h:88
#     STARTUP_HDR_VERSION   1            startup.h:89
# and QNX's own "The startup header" page, which lists the same fields in the
# same order. Summing those field widths gives 256 bytes, which the header's
# own header_size field confirms on every image tested.
#
# machine is documented as "Machine type from sys/elf.h", so it is reported
# through the ELF constants (EM_AARCH64 183, EM_ARM 40, EM_386 3, EM_X86_64 62
# from linux/include/uapi/linux/elf-em.h).
#
# The image filesystem begins at startup_size. flags1 carries the compression
# method (COMPRESS_MASK 0x1c: none 0x00, zlib 0x04, lzo 0x08, ucl 0x0c;
# startup.h:73-80). When compressed, the imagefs is a run of blocks, each a
# 2-byte big-endian compressed length followed by that many bytes, decompressing
# to at most 64 KiB, terminated by a zero length. dumpifs.c:563-595. All real
# evidence to hand is UCL, and there is no UCL decompressor in the standard
# library, so a small one is carried below rather than taking a dependency: this
# tool's whole point is that it installs nothing. zlib is handled through the
# standard library. lzo and the Harman Becker HBCIFS container are recognised but
# not decompressed here, because no sample exists to validate a reader against.
# ---------------------------------------------------------------------------
QNX_IFS_SIG = 0x00FF7EEB
QNX_IFS_VER = 1
IFS_F = dict(signature=0, version=4, flags1=6, flags2=7, header_size=8,
             machine=10, startup_vaddr=12, paddr_bias=16, image_paddr=20,
             ram_paddr=24, ram_size=28, startup_size=32, stored_size=36,
             imagefs_paddr=40, imagefs_size=44, preboot_size=48)
IFS_HDR_SIZE = 256
ELF_MACHINE = {3: "x86", 40: "ARM 32 bit", 62: "x86-64", 183: "ARM 64 bit"}

# startup_header flags1, sys/startup.h:73-80. dumpifs.c:533 switches on the
# masked value directly, so the names below are the masked constants, not shifted.
IFS_COMPRESS_MASK  = 0x1c
IFS_COMPRESS = {0x00: "none", 0x04: "zlib", 0x08: "lzo", 0x0c: "ucl"}
IFS_FLAG_BIGENDIAN = 0x02

# image_header, the "imagefs" filesystem header, sys/image.h:42-56. Every field
# is a 4-byte unsigned long (32-bit target, ILP32; dumpifs.c byte-swaps each with
# ENDIAN_RET32). image_size runs from this header to the end of the trailer;
# dir_offset is the first directory entry, hdr_dir_size the byte past the last.
IMG_SIG = b"imagefs"
IMGH = dict(flags=7, image_size=8, hdr_dir_size=12, dir_offset=16,
            boot_ino=20, script_ino=36, chain_paddr=40, mountflags=84)

# union image_dirent, sys/image.h:75-108. A flat, contiguous table of variable
# length records; each starts with the 24-byte image_attr, then a type-specific
# tail keyed on mode & S_IFMT, then the entry's full path relative to the image
# root (no leading slash). attr.size is the whole record's length and steps to
# the next entry; size 0 ends the table. attr.ino 0 means skip. There is no
# per-directory child list: the tree is carried entirely in the path strings.
IFS_ATTR = dict(size=0, extattr_offset=2, ino=4, mode=8, gid=12, uid=16, mtime=20)
IFS_ATTR_LEN = 24
# QNX sys/stat.h:210-218. S_IFNAM 0x5000 is QNX specific; the rest match Unix,
# so the shared collect()/print_tree() read dir, regular and link modes as usual.
IFS_S_IFMT, IFS_S_IFREG, IFS_S_IFDIR, IFS_S_IFLNK = 0xF000, 0x8000, 0x4000, 0xA000


def ucl_nrv2b_decompress(src):
    """Decompress one UCL NRV2B block. This is the _8 (byte at a time, MSB first)
    variant that dumpifs links as ucl_nrv2b_decompress_8. Ported field for field
    from Markus Oberhumer's UCL, src/n2b_d.c and src/getbit.h (getbit_8). The bit
    stream and the literal and offset bytes share one input cursor.

    A wrong port almost never lands on the exact target length, so the caller
    checks the concatenated output against the header's imagefs_size and the
    image trailer checksum rather than trusting this in isolation.
    """
    out = bytearray()
    ilen = 0
    bb = 0
    bits = 0
    last_m_off = 1

    def getbit():
        nonlocal bb, bits, ilen
        if bits == 0:
            bb = src[ilen]
            ilen += 1
            bits = 8
        bits -= 1
        return (bb >> bits) & 1

    while True:
        while getbit():                         # literal run
            out.append(src[ilen])
            ilen += 1
        m_off = 1                               # match offset, high part
        while True:
            m_off = m_off * 2 + getbit()
            if getbit():
                break
        if m_off == 2:                          # reuse the previous offset
            m_off = last_m_off
        else:
            m_off = (m_off - 3) * 256 + src[ilen]
            ilen += 1
            if m_off == 0xFFFFFFFF:             # end of stream
                break
            m_off += 1
            last_m_off = m_off
        m_len = getbit() * 2 + getbit()         # match length
        if m_len == 0:
            m_len = 1
            while True:
                m_len = m_len * 2 + getbit()
                if getbit():
                    break
            m_len += 2
        if m_off > 0xd00:
            m_len += 1
        pos = len(out) - m_off
        out.append(out[pos])                    # copy m_len + 1 bytes, forward,
        pos += 1                                # so overlapping runs work
        for _ in range(m_len):
            out.append(out[pos])
            pos += 1
    return bytes(out)


def ifs_decompress_blocks(stored, decompress):
    """Concatenate the decompressed blocks. Each block is a 2-byte big-endian
    compressed length then that many bytes; a zero length ends the run.
    dumpifs.c:563-595."""
    out = bytearray()
    pos = 0
    while pos + 2 <= len(stored):
        ln = struct.unpack_from(">H", stored, pos)[0]
        if ln == 0:
            break
        out += decompress(stored[pos + 2:pos + 2 + ln])
        pos += 2 + ln
    return bytes(out)


class IfsUnsupported(Exception):
    """Raised when an IFS is recognised but its contents cannot be read here,
    for example an lzo-compressed image or the HBCIFS container. The header is
    still reported; only the walk is declined, and the reason is said out loud."""


class IfsWalker:
    """List and read files from a QNX IFS boot image. The whole image filesystem
    is decompressed into memory once (a compressed block cannot be seeked into),
    then the flat directory table is parsed and a tree is built from the full
    path strings. Same interface as the other walkers, so collect(), print_tree()
    and extract_to_zip() drive it unchanged. A node is the entry's full path."""

    root = ""

    def __init__(self, fh, base):
        self.fh, self.base = fh, base
        hdr = read_at(fh, base, IFS_HDR_SIZE)
        if len(hdr) < IFS_HDR_SIZE or \
                struct.unpack_from("<I", hdr, IFS_F["signature"])[0] != QNX_IFS_SIG:
            raise IfsUnsupported("not a startup header")
        flags1 = hdr[IFS_F["flags1"]]
        if flags1 & IFS_FLAG_BIGENDIAN:
            # No big-endian IFS is to hand to validate the swap against, so the
            # walk is declined rather than guessed. The header still reports.
            raise IfsUnsupported("big-endian image, not read here")
        self.compress = IFS_COMPRESS.get(flags1 & IFS_COMPRESS_MASK, "unknown")
        ss = struct.unpack_from("<I", hdr, IFS_F["startup_size"])[0]
        st = struct.unpack_from("<I", hdr, IFS_F["stored_size"])[0]
        isz = struct.unpack_from("<I", hdr, IFS_F["imagefs_size"])[0]
        stored = read_at(fh, base + ss, st - ss)
        if self.compress == "none":
            img = stored[:isz]
        elif self.compress == "ucl":
            img = ifs_decompress_blocks(stored, ucl_nrv2b_decompress)
        elif self.compress == "zlib":
            import zlib
            img = zlib.decompress(stored)       # a single gzip stream, dumpifs.c:534
        else:
            raise IfsUnsupported(f"{self.compress} compression not read here")
        if img[:len(IMG_SIG)] != IMG_SIG:
            raise IfsUnsupported("no imagefs header after decompression")
        self.img = img
        self.image_size = struct.unpack_from("<I", img, IMGH["image_size"])[0]
        self.hdr_dir_size = struct.unpack_from("<I", img, IMGH["hdr_dir_size"])[0]
        self.dir_offset = struct.unpack_from("<I", img, IMGH["dir_offset"])[0]
        self.decompressed = len(img)
        # A byte-exact self-check that does not depend on this reader: the image
        # trailer holds a 32-bit checksum such that the 32-bit words from the
        # header to the end of the trailer sum to zero (image.h:110, and observed
        # to hold on every Sync G4 volume). A single wrong byte breaks it.
        n = self.image_size // 4
        if n * 4 <= len(img):
            total = sum(struct.unpack_from("<%dI" % n, img, 0)) & 0xFFFFFFFF
            self.cksum_ok = total == 0
        else:
            self.cksum_ok = None
        self._parse_dir()

    def _parse_dir(self):
        img = self.img
        root_mode, root_mtime = IFS_S_IFDIR, 0
        self.nodes = {}                          # path -> (mode, size, mtime)
        self.files = {}                          # path -> (offset, size)
        self.links = {}                          # path -> target string
        self.kids = {"": []}                     # path -> [(name, childpath)]
        dpos = self.dir_offset
        while dpos + IFS_ATTR_LEN <= self.hdr_dir_size:
            size = struct.unpack_from("<H", img, dpos)[0]
            if size < IFS_ATTR_LEN:              # 0 ends the table; <24 is invalid
                break
            ino = struct.unpack_from("<I", img, dpos + IFS_ATTR["ino"])[0]
            mode = struct.unpack_from("<I", img, dpos + IFS_ATTR["mode"])[0]
            mtime = struct.unpack_from("<I", img, dpos + IFS_ATTR["mtime"])[0]
            rec = img[dpos:dpos + size]
            dpos += size
            if ino == 0:
                continue
            typ = mode & IFS_S_IFMT
            if typ == IFS_S_IFREG:
                foff, fsize = struct.unpack_from("<II", rec, IFS_ATTR_LEN)
                path = rec[IFS_ATTR_LEN + 8:].split(b"\x00")[0]
                self._add(path, mode, fsize, mtime)
                self.files[path.decode("utf-8", "replace")] = (foff, fsize)
            elif typ == IFS_S_IFDIR:
                path = rec[IFS_ATTR_LEN:].split(b"\x00")[0]
                self._add(path, mode, 0, mtime)
                if path:
                    self.kids.setdefault(path.decode("utf-8", "replace"), [])
                else:
                    root_mode, root_mtime = mode, mtime
            elif typ == IFS_S_IFLNK:
                soff, ssize = struct.unpack_from("<HH", rec, IFS_ATTR_LEN)
                nb = IFS_ATTR_LEN + 4                 # name and target follow the two u16
                path = rec[nb:].split(b"\x00")[0]
                self.links[path.decode("utf-8", "replace")] = \
                    rec[nb + soff:nb + soff + ssize].decode("utf-8", "replace")
                self._add(path, mode, 0, mtime)
            else:                                # device, fifo, or QNX name special
                path = rec[IFS_ATTR_LEN + 8:].split(b"\x00")[0]
                self._add(path, mode, 0, mtime)
        self.nodes[""] = (root_mode, 0, root_mtime)

    def _add(self, path_b, mode, size, mtime):
        """Place one entry, materialising any parent directories the flat table
        left implicit (a file at a/b/c with no dirent for a or a/b)."""
        path = path_b.decode("utf-8", "replace")
        if path == "":
            return
        parts = path.split("/")
        parent = ""
        for i in range(len(parts) - 1):
            ap = "/".join(parts[:i + 1])
            if ap not in self.nodes:
                self.nodes[ap] = (IFS_S_IFDIR, 0, mtime)
                self.kids.setdefault(parent, [])
                self.kids[parent].append((parts[i], ap))
                self.kids.setdefault(ap, [])
            parent = ap
        if path not in self.nodes:
            self.kids.setdefault(parent, [])
            self.kids[parent].append((parts[-1], path))
        self.nodes[path] = (mode, size, mtime)

    def inode(self, node):
        return self.nodes.get(node)

    def listdir(self, node):
        return sorted(self.kids.get(node, []))

    def entry(self, node):
        return self.nodes.get(node)

    def read_file(self, node, size):
        off, fsize = self.files.get(node, (None, None))
        if off is None:
            return
        yield self.img[off:off + fsize]


# ---------------------------------------------------------------------------
# Extraction (--extract)
#
# Mounting a qnx6 volume is a Linux-only trick. macOS ships no qnx6 driver,
# the WSL2 kernel is built with CONFIG_QNX6FS_FS unset, and the FUSE options
# are Linux-tested. So rather than mount, the same readers that back --list
# copy the logical files straight out into a zip. Pure standard library, so it
# behaves the same on macOS, Windows and Linux, needs no administrator rights,
# and cannot write to the evidence.
# ---------------------------------------------------------------------------
def _zip_time(v):
    d = None
    try:
        d = datetime.datetime.fromtimestamp(v, datetime.timezone.utc)
    except (OverflowError, OSError, ValueError):
        pass
    if d is None or d.year < 1980:      # the zip format cannot hold earlier
        return (1980, 1, 1, 0, 0, 0)
    return (d.year, d.month, d.day, d.hour, d.minute, d.second)


def collect(w, num, prefix="", depth=0, seen=None, out=None):
    """Every regular file under this inode, as (path, inode, size, mtime)."""
    if seen is None:
        seen, out = set(), []
    if depth > 64 or num in seen:
        return out
    seen.add(num)
    for name, ino in w.listdir(num):
        ent = w.entry(ino)
        if not ent:
            continue
        mode, size, mtime = ent
        path = f"{prefix}/{name}" if prefix else name
        if mode & S_IFDIR:
            collect(w, ino, path, depth + 1, seen, out)
        elif (mode & 0o170000) == 0o100000:          # regular files only
            out.append((path, ino, size, mtime))
        else:
            out.append((path, ino, None, mtime))     # symlink or special
    return out


def apply_exclude(entries, exclude):
    """Drop entries whose path contains any excluded substring."""
    if not exclude:
        return entries, 0
    keep = [e for e in entries if not any(x in e[0] for x in exclude)]
    return keep, len(entries) - len(keep)


class ProgressEmitter:
    """Throttled machine-readable extraction progress, one JSON object per line.

    Extraction of a head unit volume runs for minutes with nothing on stdout
    until the volume finishes, which reads as a hang to anything driving this
    as a subprocess. --progress emits to STDERR so the human report on stdout
    is untouched and a caller can consume one stream without parsing the other.

    Each line carries exact counts for the volume being written, not estimates:

        {"volume": "@13168672", "files": 1234, "total_files": 1629,
         "bytes": 123456789, "total_bytes": 297023717}

    Throttled to one line per interval, plus a final line per volume so a
    consumer always sees the completed state whatever the timing.
    """

    def __init__(self, stream=None, interval=1.0, clock=time.monotonic):
        self.stream = stream if stream is not None else sys.stderr
        self.interval = interval
        self.clock = clock
        self.last = 0.0

    def __call__(self, volume, files, written, total_files, total_bytes):
        now = self.clock()
        done = total_files and files >= total_files
        if not done and now - self.last < self.interval:
            return
        self.last = now
        self.stream.write(json.dumps({
            "volume": volume, "files": files, "total_files": total_files,
            "bytes": written, "total_bytes": total_bytes,
        }) + "\n")
        self.stream.flush()


def extract_to_zip(zf, w, volume, entries, log, progress=None):
    """Stream each regular file into the open zipfile. Returns a tally.

    progress, when given, is called after each file with
    (volume, files_done, written_bytes, total_files, total_bytes). The totals
    are exact rather than estimated: entries is already the full list for this
    volume, so both are known before the first file is written.
    """
    total_files = sum(1 for _, _, size, _ in entries if size is not None)
    total_bytes = sum(size for _, _, size, _ in entries if size is not None)
    files = written = skipped = failed = 0
    for path, ino, size, mtime in entries:
        arc = f"{volume}/{path}"
        if size is None:
            skipped += 1
            continue
        try:
            info = zipfile.ZipInfo(arc, date_time=_zip_time(mtime))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with zf.open(info, "w") as dst:
                for chunk in w.read_file(ino, size):
                    dst.write(chunk)
            files += 1
            written += size
        except Exception as exc:
            failed += 1
            log.append(f"        could not extract {arc}: {exc}")
        if progress is not None:
            progress(volume, files, written, total_files, total_bytes)
    return files, written, skipped, failed


# ---------------------------------------------------------------------------
# Triage (--triage)
#
# A head unit can run to tens of gigabytes and most of it is not evidence.
# This ranks what was found so an examiner can decide what to pull first,
# using only what the probe already read.
#
# Two axes, because they disagree and that is the point:
#   ACTIVITY  how much the volume has been written. qnx6 exposes a commit
#             counter in the superblock serial; ext exposes mount count and
#             lifetime kilobytes written. This finds the user-data volume.
#   DENSITY   value per byte. A 4 MiB manufacturing volume holding the unit's
#             addresses, serials and keys outranks 25 GiB of map data on any
#             question an examiner is likely to ask.
#
# Ranking on size alone gets this backwards, which is why both are printed
# rather than combined into one score.
# ---------------------------------------------------------------------------
ENCRYPTED_NAME_MARKERS = ("ECRYPTFS_FNEK_ENCRYPTED",)


def sample_encryption(w, limit=400):
    """Fraction of sampled names that look like encrypted filenames."""
    from collections import deque
    seen = enc = 0
    queue = deque([w.root])
    while queue and seen < limit:
        num = queue.popleft()
        try:
            kids = w.listdir(num)
        except Exception:
            continue
        for name, ino in kids:
            seen += 1
            if any(mk in name for mk in ENCRYPTED_NAME_MARKERS):
                enc += 1
            if seen >= limit:
                break
            ent = w.entry(ino)
            if ent and ent[0] & S_IFDIR and len(queue) < 512:
                queue.append(ino)
    return enc, seen


def triage_row(label, kind, size, used, activity, act_note, when, enc):
    return dict(label=label, kind=kind, size=size, used=used,
                activity=activity, act_note=act_note, when=when, enc=enc)


def print_triage(rows):
    if not rows:
        return
    print("\n" + "=" * 78)
    print("  TRIAGE  what to pull first")
    print("=" * 78)
    print("  Ranked by how much each volume has been written. Read the density")
    print("  column too: a small volume can outrank a large one.\n")
    rows = sorted(rows, key=lambda r: -(r["activity"] or 0))
    print(f"  {'volume':<26}{'type':<10}{'used':>11}{'activity':>14}  last write")
    print("  " + "-" * 74)
    for r in rows:
        act = f"{r['activity']:,}" if r["activity"] is not None else "-"
        print(f"  {r['label'][:25]:<26}{r['kind'][:9]:<10}{human(r['used']):>11}"
              f"{act:>14}  {r['when']}")
        notes = []
        if r["act_note"]:
            notes.append(r["act_note"])
        if r["enc"] and r["enc"][1]:
            e, t = r["enc"]
            if e:
                notes.append(f"{100*e//t}% of sampled names are ENCRYPTED, "
                             f"so contents are not parseable without keys")
        if r["size"]:
            pct = 100.0 * (r["used"] or 0) / r["size"]
            notes.append(f"{pct:.0f}% full of {human(r['size'])}")
        for nline in notes:
            print(f"  {'':<26}{nline}")
    print()
    print("  Pull the top of this list first, then any small volume whose name")
    print("  suggests manufacturing, identity or configuration. Skip volumes")
    print("  that are mostly empty bulk, and do not spend time on encrypted")
    print("  ones until you have the keys.")
    print()


def identify_ifs(fh, base):
    """Return detail lines if a QNX IFS boot image starts here, else None."""
    h = read_at(fh, base, IFS_HDR_SIZE)
    if len(h) < IFS_HDR_SIZE:
        return None
    g32 = lambda k: struct.unpack_from("<I", h, IFS_F[k])[0]
    g16 = lambda k: struct.unpack_from("<H", h, IFS_F[k])[0]
    if g32("signature") != QNX_IFS_SIG:
        return None
    hsz, ver, mach = g16("header_size"), g16("version"), g16("machine")
    ss, st, ifs_sz = g32("startup_size"), g32("stored_size"), g32("imagefs_size")
    flags1 = h[IFS_F["flags1"]]
    method = IFS_COMPRESS.get(flags1 & IFS_COMPRESS_MASK, "unknown")
    endian = "big" if flags1 & IFS_FLAG_BIGENDIAN else "little"

    lines = [f"version      {ver}" + ("" if ver == QNX_IFS_VER
                                      else f"   (STARTUP_HDR_VERSION is {QNX_IFS_VER})"),
             f"header_size  {hsz}" + ("   agrees with the 256-byte struct"
                                      if hsz == IFS_HDR_SIZE else
                                      "   DOES NOT match the 256-byte struct"),
             f"machine      {mach}  ({ELF_MACHINE.get(mach, 'unrecognised ELF machine')})",
             f"flags        0x{flags1:02x} 0x{h[IFS_F['flags2']]:02x}"
             f"   {endian} endian, {method} compression"
             f"   startup_vaddr 0x{g32('startup_vaddr'):08x}",
             f"startup      {human(ss)} of startup code, image filesystem begins at "
             f"0x{ss:x}"]

    stored_ifs = st - ss
    if stored_ifs == ifs_sz:
        how = "stored uncompressed"
    elif 0 < stored_ifs < ifs_sz:
        how = f"stored {method} compressed, {human(ifs_sz)} into {human(stored_ifs)}"
    else:
        how = "stored size and imagefs size disagree"
    lines.append(f"imagefs      {human(ifs_sz)} uncompressed, {how}")
    lines.append(f"total        {human(st)} stored on the partition")

    if method in ("ucl", "zlib", "none") and endian == "little":
        lines.append("contents     listed and extracted with --list and --extract")
    elif endian == "big":
        lines.append("contents     big-endian image, header reported but not walked here")
    elif method == "lzo":
        lines.append("contents     lzo compressed, not read here (no sample to "
                     "validate a reader), see --help")
    else:
        lines.append(f"contents     {method} compression, not read here, see --help")
    return lines


def walker_for(kind, fh, base, size=None):
    """The walker class for a filesystem kind, or None if it has no walker.

    ETFS needs the region size (to page the flash) and its detected page size,
    so callers that want an ETFS walker must pass size.
    """
    if kind and kind.startswith("ext"):
        return ExtWalker(fh, base)
    if kind == "fat32":
        return Fat32Walker(fh, base)
    if kind == "exfat":
        return ExfatWalker(fh, base)
    if kind == "efs":
        return EfsWalker(fh, base)
    if kind == "etfs" and size is not None:
        P = etfs_pagesize(fh, base, size)
        return EtfsWalker(fh, base, size, P) if P else None
    if kind == "QNX IFS boot image":
        return IfsWalker(fh, base)
    return None


def _etfs_reserved_match(fh, base, pagesize, n, need=3):
    """True if a fid==1 cluster-0 page parses into a .filetable carrying the
    fixed reserved names at their fixed ids and a directory at the root id.

    The reserved-name check is what makes ETFS detection specific: ETFS has no
    magic number, so a bare page-count match would be a coincidence, but the
    names .filetable/.badblks/.counts at fixed file ids are not.
    """
    per = pagesize // ETFS_ENTRY_SIZE
    if per < 6:                                      # too small to hold fids 0..5
        return False
    unit = pagesize + ETFS_TRANS_SIZE
    for pi, fid, cluster, ta, seq in _etfs_scan_transactions(
            fh, base, pagesize, n, want_fid=ETFS_FID_FTABLE, cap=min(n, 200000)):
        if cluster != 0:
            continue
        data = read_at(fh, base + pi * unit, pagesize)
        r = _etfs_parse_entry(data[0:ETFS_ENTRY_SIZE])
        if not (r and r["body"] and (r["body"]["mode"] & 0o170000) == S_IFDIR):
            continue
        hits = 0
        for rid, name in ETFS_RESERVED.items():
            e = _etfs_parse_entry(data[rid * ETFS_ENTRY_SIZE:(rid + 1) * ETFS_ENTRY_SIZE])
            if e and e["body"] and e["body"].get("name") == name:
                hits += 1
        if hits >= need:
            return True
    return False


def etfs_pagesize(fh, base, size):
    """The ETFS page size for the region, or None. A candidate is accepted only
    when the region divides evenly into (pagesize + 16)-byte pages AND the
    .filetable carries its reserved names, so a chance size match is rejected.
    """
    for P in ETFS_PAGE_SIZES:
        unit = P + ETFS_TRANS_SIZE
        if size < unit or size % unit != 0:
            continue
        if _etfs_reserved_match(fh, base, P, size // unit):
            return P
    return None


def identify_etfs(fh, base, size):
    """Return ("etfs", lines) if an ETFS filesystem fills this region, else None."""
    P = etfs_pagesize(fh, base, size)
    if P is None:
        return None
    return "etfs", [
        f"page size    {P:,} bytes data + {ETFS_TRANS_SIZE} bytes transaction",
        f"pages        {size // (P + ETFS_TRANS_SIZE):,}",
        "layout       transaction based, live state replayed from the spare area",
        "reserved     .filetable/.badblks/.counts/.lost+found/.reserved present",
    ]


def identify_efs(fh, base, size):
    """Return ("efs", lines) if an EFS (F3S) filesystem starts at base, else None."""
    us = _efs_unit_size(fh, base)
    if us is None:
        return None
    boot = _efs_boot(fh, base, min(us * 4, 1 << 24))
    if boot is None:
        return None
    if boot["unit_total"] < 1 or boot["unit_total"] * us > size:
        return None
    return "efs", [
        f"unit size    {human(us)}   {boot['unit_total']} units, "
        f"{boot['unit_spare']} spare",
        f"alignment    text offsets shifted left by {boot['align_pow2']}",
        f"boot record  QSSL_F3S at +0x{boot['sig_at']:x}",
        f"root         logical unit {boot['root'][0]}, extent {boot['root'][1]}",
    ]


def identify_fat(fh, base):
    """Return (kind, lines) for a FAT32 or exFAT volume at base, else None.

    exFAT names itself in bytes 3..11 of the boot sector. FAT32 is recognised
    by its "FAT32   " filesystem-type string at offset 82 together with a 0x55AA
    boot signature, rather than by the OEM name, which is set by whatever tool
    wrote the volume.
    """
    b = read_at(fh, base, 512)
    if len(b) < 512 or b[510:512] != b"\x55\xaa":
        if b[3:11] != b"EXFAT   ":
            return None
    if b[3:11] == b"EXFAT   ":
        bps = 1 << b[108]
        spc = 1 << b[109]
        clusters = struct.unpack_from("<I", b, 92)[0]
        vol = struct.unpack_from("<Q", b, 72)[0] * bps
        return "exfat", [
            f"bytes/sector {bps}   sectors/cluster {spc}",
            f"clusters     {clusters:,}",
            f"volume       {human(vol)}",
        ]
    if b[82:90] == b"FAT32   ":
        bps = struct.unpack_from("<H", b, 11)[0]
        spc = b[13]
        total = struct.unpack_from("<I", b, 32)[0] * bps
        label = b[71:82].decode("ascii", "replace").rstrip(" ")
        return "fat32", [
            f"label        {label or '(none)'}",
            f"bytes/sector {bps}   sectors/cluster {spc}",
            f"volume       {human(total)}",
        ]
    return None


def identify_fs(fh, base, size=None):
    """Return (name, [detail lines]) for whatever sits at this partition.

    size is the region's byte length, needed by the flash filesystems (ETFS/EFS)
    which have no header at a fixed offset and are sized by the region. When it
    is not given it is taken as the rest of the file from base.
    """
    if size is None:
        try:
            size = os.fstat(fh.fileno()).st_size - base
        except OSError:
            size = 0
    sb = read_at(fh, base + EXT_SB_OFF, 1024)
    if len(sb) == 1024 and _e(sb, "magic", 2) == EXT_MAGIC:
        bs = 1024 << _e(sb, "log_block_size")
        total = _e(sb, "blocks_count") * bs
        free = _e(sb, "free_blocks") * bs
        inc, cmp_ = _e(sb, "feature_incompat"), _e(sb, "feature_compat")
        kind = ("ext4" if inc & EXT_INCOMPAT_EXTENTS
                else "ext3" if cmp_ & EXT_COMPAT_HAS_JOURNAL else "ext2")
        label = sb[EXT_F["volume_name"]:EXT_F["volume_name"] + 16]
        label = label.split(b"\x00")[0].decode("utf-8", "replace")
        lastm = sb[EXT_F["last_mounted"]:EXT_F["last_mounted"] + 64]
        lastm = lastm.split(b"\x00")[0].decode("utf-8", "replace")
        uid = sb[EXT_F["uuid"]:EXT_F["uuid"] + 16].hex()
        st = _e(sb, "state", 2)
        used = total - free
        lines = [
            f"label        {label or '(none)'}",
            f"last mounted {lastm or '(none)'}",
            f"uuid         {uid}",
            f"made         {stamp(_e(sb, 'mkfs_time'))}",
            f"last mount   {stamp(_e(sb, 'mtime'))}   mount count "
            f"{_e(sb, 'mnt_count', 2):,}",
            f"last write   {stamp(_e(sb, 'wtime'))}",
            f"used         {human(used)} of {human(total)} "
            f"({100.0*used/total:.1f}%)" if total else "used         unknown",
            f"written      {_e(sb, 'kbytes_written', 8)/1048576:,.1f} GiB over its life",
            f"state        0x{st:04x}  "
            + ("cleanly unmounted" if st & EXT_VALID_FS
               else "NOT cleanly unmounted, so it may have been live at acquisition"),
        ]
        ec = _e(sb, "error_count")
        if ec:
            lines.append(f"errors       {ec:,} recorded")
        return kind, lines

    ifs = identify_ifs(fh, base)
    if ifs:
        return "QNX IFS boot image", ifs

    fat = identify_fat(fh, base)
    if fat:
        return fat

    efs = identify_efs(fh, base, size)
    if efs:
        return efs

    etfs = identify_etfs(fh, base, size)
    if etfs:
        return etfs

    # Not ext, not qnx6, not IFS, not FAT, not a QNX flash filesystem. Report
    # the leading bytes so there is a lead to follow, rather than inventing a
    # signature for it.
    head = read_at(fh, base, 16)
    if not head:
        return None, []
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in head)
    ascii_magic = ""
    run = bytes(c for c in head[:8] if 32 <= c < 127)
    if len(run) >= 3:
        ascii_magic = f'   leading ascii "{run.decode()}"'
    return None, [f"first 16 bytes  {head.hex(' ')}",
                  f"                |{printable}|{ascii_magic}"]


def human(n):
    if abs(n) < 1024:
        return f"{n:,.0f} B"
    n /= 1024
    for u in ("KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024:
            return f"{n:,.1f} {u}"
        n /= 1024
    return f"{n:,.1f} PiB"


def scan(fh, limit, size, cap=400):
    hits, step = [], 1 << 22
    pats = ((struct.pack("<I", QNX6_MAGIC), 1), (struct.pack(">I", QNX6_MAGIC), 1))
    off = 0
    while off < min(limit, size) and len(hits) < cap:
        buf = read_at(fh, off, step + 4)
        if not buf:
            break
        for pat, _ in pats:
            p = buf.find(pat)
            while p != -1 and len(hits) < cap:
                hits.append(off + p)
                p = buf.find(pat, p + 1)
        off += step
    return sorted(set(hits))


def sanitize_volume_label(label, max_len=24):
    """A partition or filesystem label, reduced to zip-and-shell-safe form."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()
    return cleaned[:max_len].rstrip("_")


def volume_name(part_idx, lba, label=""):
    """The canonical directory name a volume extracts under.

    Built from the partition table, not from the filesystem: the LBA is a
    physical fact about the image that any partition tool reproduces, so it is
    the identity, and it cannot collide because two volumes cannot share a
    start sector. The index gives readability where a table provides one, and
    a label rides along as a suffix, never as the identity, so two partitions
    labelled alike still extract into distinct directories.

        p2_lba65536                   MBR primary 2
        p5_lba4259872                 first logical volume (numbered from 5,
                                      as operating systems do)
        p9_lba737280_storage          GPT partition with its name
        lba0                          no partition table at all: a whole-disk
                                      filesystem or a bare region, which is
                                      how ETFS commonly arrives

    The earlier scheme took the last word of the display label, which made
    "...System Partition" and "...Data Partition" extract into the same
    directory and silently merge.
    """
    stem = f"p{part_idx}_lba{lba}" if part_idx is not None else f"lba{lba}"
    suffix = sanitize_volume_label(label) if label else ""
    return f"{stem}_{suffix}" if suffix else stem


def main(path, scan_limit_mib=256, do_list=False, list_depth=2, list_max=400,
         extract=None, only=None, zf=None, do_triage=False, exclude=None,
         reporter=None, manifest=None):
    size = os.path.getsize(path)
    print("=" * 78)
    print(path)
    print(f"  {size:,} bytes ({human(size)})")
    print("=" * 78)

    candidates, regions, sized_regions, triage = [], [], [], []
    containers, protective = set(), set()
    vol_names = {}                    # byte offset -> canonical extract name
    with open(path, "rb") as fh:
        parts = parse_mbr(fh)
        if parts is None:
            print("  MBR      no 0x55AA signature at offset 510")
        else:
            gpt_prot = any(t == 0xEE for _, t, _, _ in parts)
            print(f"  MBR      valid, {len(parts)} entries"
                  + ("  (0xEE = GPT protective)" if gpt_prot else ""))
            for idx, t, st, cnt in parts:
                tag = f"   <- {MBR_QNX_TYPES[t]}" if t in MBR_QNX_TYPES else ""
                print(f"    {idx}  type 0x{t:02x}  LBA {st:<12,} {human(cnt*SECTOR):>10}{tag}")
                regions.append((f"MBR part {idx}", st * SECTOR))
                sized_regions.append((f"MBR part {idx}", st * SECTOR, cnt * SECTOR))
                vol_names[st * SECTOR] = volume_name(idx, st)
                if t in (0x05, 0x0f, 0x85):
                    containers.add(f"MBR part {idx}")
                if t == 0xEE:
                    protective.add(f"MBR part {idx}")

        # An extended partition holds the logical volumes; walk the EBR chain,
        # or the largest region of the image is never probed at all.
        EXT = (0x05, 0x0f, 0x85)
        logical_idx = 4               # logical volumes number from 5, as OSes do
        for idx, t, st, cnt in (parts or []):
            if t not in EXT:
                continue
            base, cur, n = st, st, 0
            while cur and n < 64:
                ebr = read_at(fh, cur * SECTOR, 512)
                if len(ebr) < 512 or ebr[510:512] != b"\x55\xaa":
                    break
                e1 = ebr[446:462]; e2 = ebr[462:478]
                lt = e1[4]; lst, lcnt = struct.unpack("<II", e1[8:16])
                if lcnt:
                    astart = cur + lst
                    tag = f"   <- {MBR_QNX_TYPES[lt]}" if lt in MBR_QNX_TYPES else ""
                    print(f"      logical  type 0x{lt:02x}  LBA {astart:<12,}"
                          f" {human(lcnt*SECTOR):>10}{tag}")
                    regions.append((f"logical @{astart}", astart * SECTOR))
                    sized_regions.append((f"logical @{astart}", astart * SECTOR,
                                          lcnt * SECTOR))
                    logical_idx += 1
                    vol_names[astart * SECTOR] = volume_name(logical_idx, astart)
                nxt = struct.unpack("<I", e2[8:12])[0]
                cur = (base + nxt) if nxt else 0
                n += 1

        gpt = parse_gpt(fh)
        if gpt:
            print(f"\n  GPT      valid, {len(gpt)} partition entries")
            for idx, name, g, first, last in gpt:
                sz = (last - first + 1) * SECTOR
                print(f"    {idx:>3}  {name[:26]:<26} {human(sz):>10}  LBA {first:,}")
                regions.append((f"GPT part {idx} {name[:20]}", first * SECTOR))
                sized_regions.append((f"GPT part {idx} {name[:20]}", first * SECTOR, sz))
                vol_names[first * SECTOR] = volume_name(idx, first, name)

        # No partition table at all (a whole-disk filesystem, or a bare region
        # such as an ETFS flash dump) means no regions were recorded. Treat the
        # whole image as one region so it still reaches identify_fs and the
        # walkers, named lba0 by the volume_name fallback.
        if not sized_regions:
            sized_regions.append(("whole image", 0, size))
            regions.append(("whole image", 0))
            vol_names[0] = volume_name(None, 0)

        # the two offsets the kernel itself probes, per region and whole-image
        print()
        for label, base in [("image start", 0)] + regions:
            for off, rel in sb_slots(fh, base, label, sized_regions):
                r = check(fh, off)
                if r:
                    candidates.append((off, f"{label} +0x{rel:x}", *r))

        if not candidates:
            print(f"  no superblock at the kernel's offsets; brute scanning first"
                  f" {scan_limit_mib} MiB ...")
            for off in scan(fh, scan_limit_mib << 20, size):
                r = check(fh, off)
                if r:
                    candidates.append((off, "brute scan", *r))

        print()
        # A candidate whose volume id, blocksize and block count match an
        # already-confirmed superblock in the SAME region is another copy of
        # that filesystem, not a chance 4-byte hit. Measured on a Ford Sync G4
        # image: the previous generation of dps_os carries ctime 308 and
        # atime 1, both unset because the build host had no clock, so a
        # timestamp heuristic rejects a genuine superblock. Recorded identity
        # is the stronger signal, so it wins.
        def region(h):
            return h.rsplit(" +0x", 1)[0]
        good = {}
        for off, how, endian, sb, bad in candidates:
            if not bad:
                good.setdefault(region(how), []).append(sb)
        promoted = 0
        for i, (off, how, endian, sb, bad) in enumerate(candidates):
            if not bad:
                continue
            for ref in good.get(region(how), []):
                if (sb["volumeid"] == ref["volumeid"]
                        and sb["blocksize"] == ref["blocksize"]
                        and sb["num_blocks"] == ref["num_blocks"]):
                    candidates[i] = (off, how, endian, sb, [])
                    promoted += 1
                    break

        confirmed = [c for c in candidates if not c[4]]
        rejected  = [c for c in candidates if c[4]]
        if promoted:
            print(f"  {promoted} further cop{'y' if promoted==1 else 'ies'} "
                  f"confirmed by matching volume id, blocksize and block count\n")

        print(f"  {len(candidates)} magic match(es): "
              f"{len(confirmed)} CONFIRMED, {len(rejected)} rejected as coincidence\n")

        # Group the copies by volume, then by serial. The highest serial is
        # the active generation; the one below it is the previous committed
        # state, still on disk.
        vols = {}
        for off, how, endian, sb, _ in confirmed:
            key = how.rsplit(" +0x", 1)[0]
            vols.setdefault(key, []).append((off, endian, sb))

        if vols:
            print("  HOW TO READ THE TIMESTAMPS  (see --help for the sourcing)")
            print("    sb_ctime is written once when the filesystem is made.")
            print("    sb_atime moves when the filesystem is COMMITTED, not when a file")
            print("    is read. Do not read it as when the device was last used by a")
            print("    person. serial counts commits and is the better measure of how")
            print("    much a volume has been written.")
            print()

        for key, copies in vols.items():
            gens = {}
            for off, endian, sb in copies:
                g = gens.setdefault(sb["serial"], {"sb": sb, "endian": endian, "at": []})
                g["at"].append(off)
            serials = sorted(gens, reverse=True)
            act = gens[serials[0]]
            sb, endian = act["sb"], act["endian"]
            total = sb["num_blocks"] * sb["blocksize"]

            print(f"  CONFIRMED qnx6 filesystem on {key}  [{endian}]")
            print(f"      {len(copies)} superblock cop{'y' if len(copies)==1 else 'ies'}, "
                  f"{len(serials)} generation{'' if len(serials)==1 else 's'}\n")

            match = ""
            for rlabel, rbase, rsize in sized_regions:
                if key.startswith(rlabel) and rsize:
                    match = (f"   <- {100.0*total/rsize:.1f}% of the "
                             f"{human(rsize)} partition it sits in")
                    break

            print(f"      ACTIVE   serial {sb['serial']:,}   at "
                  + ", ".join(f"0x{o:x}" for o in sorted(act["at"])))
            print(f"        sb_ctime   {stamp(sb['ctime'])}")
            print(f"        sb_atime   {stamp(sb['atime'])}")
            print(f"        version    {sb['version1']}.{sb['version2']}   "
                  f"blocksize {sb['blocksize']:,}   flags 0x{sb['flags']:08x}")
            print(f"        volume     {human(total)}  ({sb['num_blocks']:,} blocks, "
                  f"{sb['free_blocks']:,} free){match}")
            print(f"        inodes     {sb['num_inodes']:,} total, "
                  f"{sb['free_inodes']:,} free, "
                  f"{sb['num_inodes']-sb['free_inodes']:,} used")
            print(f"        volumeid   {sb['volumeid'].hex()}  (as stored)")

            if len(serials) > 1:
                prev = gens[serials[1]]
                pb = prev["sb"]
                print(f"\n      PREVIOUS serial {pb['serial']:,}   at "
                      + ", ".join(f"0x{o:x}" for o in sorted(prev["at"]))
                      + "   (still on disk)")
                print(f"        sb_ctime   {stamp(pb['ctime'])}")
                print(f"        sb_atime   {stamp(pb['atime'])}")

                print(f"\n      WHAT CHANGED between the two generations")
                d_ser = sb['serial'] - pb['serial']
                print(f"        serial       +{d_ser:,}"
                      f"   ({'one commit' if d_ser==1 else str(d_ser)+' commits'})")
                print(delta_line("sb_ctime", sb['ctime'], pb['ctime']))
                print(delta_line("sb_atime", sb['atime'], pb['atime']))
                for f, lab in (("free_blocks","block"), ("free_inodes","inode")):
                    d = sb[f] - pb[f]
                    if d == 0:
                        print(f"        {f:<12} unchanged")
                    else:
                        word = lab + ("" if abs(d) == 1 else "s")
                        verb = "freed" if d > 0 else "allocated"
                        print(f"        {f:<12} {d:+,}  ({abs(d):,} {word} {verb})")

            base = next((b for lab, b, _ in sized_regions
                         if key.startswith(lab)), None)
            wanted = only is None or only.lower() in key.lower()

            if do_triage and base is not None:
                encf = (0, 0)
                try:
                    tw = Qnx6Walker(fh, base, sorted(act["at"])[0] - base)
                    encf = sample_encryption(tw)
                except Exception:
                    pass
                used = (sb["num_blocks"] - sb["free_blocks"]) * sb["blocksize"]
                triage.append(triage_row(
                    key.split("part", 1)[-1].strip() if "part" in key else key,
                    "qnx6", sb["num_blocks"] * sb["blocksize"], used,
                    sb["serial"], f"{sb['serial']:,} commits, "
                    f"{sb['num_inodes'] - sb['free_inodes']:,} inodes used",
                    stamp(sb["atime"]).replace(" UTC", ""), encf))

            if do_list and base is not None and wanted:
                print(f"\n      CONTENTS  (depth {list_depth})")
                try:
                    w = Qnx6Walker(fh, base, sorted(act["at"])[0] - base)
                    print_tree(w, w.root, 1, list_depth, [list_max])
                except Exception as exc:
                    print(f"        could not walk this filesystem: {exc}")

            if zf is not None and base is not None and wanted:
                vol = vol_names.get(base) or f"lba{base // SECTOR}"
                print(f"\n      EXTRACTING to {extract}  as {vol}/")
                try:
                    w = Qnx6Walker(fh, base, sorted(act["at"])[0] - base)
                    ents = collect(w, w.root)
                    ents, dropped = apply_exclude(ents, exclude)
                    log = []
                    f_, wr, sk, fa = extract_to_zip(zf, w, vol, ents, log, reporter)
                    if manifest is not None:
                        rsize = next((r[2] for r in sized_regions if r[1] == base), None)
                        manifest.append({
                            "volume": vol, "image": os.path.basename(path),
                            "lba": base // SECTOR, "offset_bytes": base,
                            "partition_size_bytes": rsize,
                            "filesystem": "qnx6",
                            "volume_id_as_stored": sb["volumeid"].hex(),
                            "superblock_serial": sb["serial"],
                            "files": f_, "bytes": wr,
                            "symlinks_or_special_skipped": sk,
                            "failed": fa, "excluded": dropped,
                        })
                    print(f"        {f_:,} files, {human(wr)}"
                          + (f", {sk:,} symlinks or special files skipped" if sk else "")
                          + (f", {fa:,} FAILED" if fa else "")
                          + (f", {dropped:,} excluded" if dropped else ""))
                    for line in log[:5]:
                        print(line)
                except Exception as exc:
                    print(f"        could not extract this filesystem: {exc}")
            print()

        # A type byte is a label, not a fact, so read the partitions that did
        # not turn out to be qnx6 rather than trusting what they claim to be.
        others = [(lab, b, sz) for lab, b, sz in sized_regions
                  if lab not in vols and lab not in protective]
        if others:
            print("  WHAT IS IN THE OTHER PARTITIONS")
            for lab, b, sz in others:
                if lab in containers:
                    print(f"    {lab}   {human(sz)}   ->  extended partition "
                          f"container, holds the logical volumes below")
                    print()
                    continue
                kind, lines = identify_fs(fh, b, sz)
                print(f"    {lab}   {human(sz)}   ->  {kind or 'not recognised'}")
                for line in lines:
                    print(f"        {line}")
                ext_name = ""
                if kind and kind.startswith("ext"):
                    _sb = read_at(fh, b + EXT_SB_OFF, 1024)
                    _l = _sb[EXT_F["volume_name"]:EXT_F["volume_name"] + 16]
                    _l = _l.split(b"\x00")[0].decode("utf-8", "replace")
                    _m = _sb[EXT_F["last_mounted"]:EXT_F["last_mounted"] + 64]
                    _m = _m.split(b"\x00")[0].decode("utf-8", "replace")
                    ext_name = _l or _m.strip("/").replace("/", "_")
                wanted = (only is None or only.lower() in lab.lower()
                          or (ext_name and only.lower() in ext_name.lower()))

                if do_triage and kind and kind.startswith("ext"):
                    esb = read_at(fh, b + EXT_SB_OFF, 1024)
                    ebs = 1024 << _e(esb, "log_block_size")
                    etot = _e(esb, "blocks_count") * ebs
                    eused = etot - _e(esb, "free_blocks") * ebs
                    kb = _e(esb, "kbytes_written", 8)
                    lbl = esb[EXT_F["volume_name"]:EXT_F["volume_name"] + 16]
                    lbl = lbl.split(b"\x00")[0].decode("utf-8", "replace")
                    mnt = esb[EXT_F["last_mounted"]:EXT_F["last_mounted"] + 64]
                    mnt = mnt.split(b"\x00")[0].decode("utf-8", "replace")
                    encf = (0, 0)
                    try:
                        encf = sample_encryption(ExtWalker(fh, b))
                    except Exception:
                        pass
                    triage.append(triage_row(
                        lbl or mnt or lab, kind, etot, eused, kb,
                        f"{kb/1048576:,.0f} GiB written over its life, "
                        f"{_e(esb, 'mnt_count', 2):,} mounts"
                        + (f", mounts at {mnt}" if mnt else ""),
                        stamp(_e(esb, "mtime")).replace(" UTC", ""), encf))

                if do_list and kind and kind.startswith("ext") and wanted:
                    print(f"        CONTENTS  (depth {list_depth})")
                    try:
                        w = ExtWalker(fh, b)
                        print_tree(w, w.root, 1, list_depth, [list_max], pad=8)
                    except Exception as exc:
                        print(f"        could not walk this filesystem: {exc}")
                if zf is not None and kind and kind.startswith("ext") and wanted:
                    stem = vol_names.get(b) or f"lba{b // SECTOR}"
                    suffix = sanitize_volume_label(ext_name) if ext_name else ""
                    vol = (f"{stem}_{suffix}"
                           if suffix and not stem.endswith(f"_{suffix}") else stem)
                    print(f"        EXTRACTING to {extract}  as {vol}/")
                    try:
                        w = ExtWalker(fh, b)
                        ents = collect(w, w.root)
                        ents, dropped = apply_exclude(ents, exclude)
                        log = []
                        f_, wr, sk, fa = extract_to_zip(zf, w, vol, ents, log, reporter)
                        if manifest is not None:
                            _u = read_at(fh, b + EXT_SB_OFF, 1024)
                            manifest.append({
                                "volume": vol, "image": os.path.basename(path),
                                "lba": b // SECTOR, "offset_bytes": b,
                                "partition_size_bytes": sz,
                                "filesystem": kind,
                                "uuid": _u[EXT_F["uuid"]:EXT_F["uuid"] + 16].hex(),
                                "label": ext_name,
                                "files": f_, "bytes": wr,
                                "symlinks_or_special_skipped": sk,
                                "failed": fa, "excluded": dropped,
                            })
                        print(f"            {f_:,} files, {human(wr)}"
                              + (f", {sk:,} symlinks or special files skipped" if sk else "")
                              + (f", {fa:,} FAILED" if fa else "")
                              + (f", {dropped:,} excluded" if dropped else ""))
                        for line in log[:5]:
                            print(line)
                    except Exception as exc:
                        print(f"        could not extract: {exc}")

                if kind in ("fat32", "exfat", "etfs", "efs") and wanted:
                    if do_list:
                        print(f"        CONTENTS  (depth {list_depth})")
                        try:
                            w = walker_for(kind, fh, b, sz)
                            print_tree(w, w.root, 1, list_depth, [list_max], pad=8)
                        except Exception as exc:
                            print(f"        could not walk this filesystem: {exc}")
                    if zf is not None:
                        vol = vol_names.get(b) or f"lba{b // SECTOR}"
                        print(f"        EXTRACTING to {extract}  as {vol}/")
                        try:
                            w = walker_for(kind, fh, b, sz)
                            ents = collect(w, w.root)
                            ents, dropped = apply_exclude(ents, exclude)
                            log = []
                            f_, wr, sk, fa = extract_to_zip(zf, w, vol, ents, log, reporter)
                            if manifest is not None:
                                manifest.append({
                                    "volume": vol, "image": os.path.basename(path),
                                    "lba": b // SECTOR, "offset_bytes": b,
                                    "partition_size_bytes": sz, "filesystem": kind,
                                    "files": f_, "bytes": wr,
                                    "symlinks_or_special_skipped": sk,
                                    "failed": fa, "excluded": dropped,
                                })
                            print(f"            {f_:,} files, {human(wr)}"
                                  + (f", {sk:,} symlinks or special files skipped" if sk else "")
                                  + (f", {fa:,} FAILED" if fa else "")
                                  + (f", {dropped:,} excluded" if dropped else ""))
                            for line in log[:5]:
                                print(line)
                        except Exception as exc:
                            print(f"        could not extract: {exc}")

                if (kind == "QNX IFS boot image" and wanted
                        and (do_list or zf is not None)):
                    w = None
                    try:
                        w = IfsWalker(fh, b)
                    except IfsUnsupported as exc:
                        print(f"        contents not read: {exc}")
                    except Exception as exc:
                        print(f"        could not read this image filesystem: {exc}")
                    if w is not None:
                        ck = ("image checksum balances" if w.cksum_ok
                              else "IMAGE CHECKSUM DOES NOT BALANCE" if w.cksum_ok is False
                              else "image checksum not checked")
                        print(f"        decoded {human(w.decompressed)} imagefs "
                              f"({w.compress}), {ck}")
                        if do_list:
                            print(f"        CONTENTS  (depth {list_depth})")
                            try:
                                print_tree(w, w.root, 1, list_depth, [list_max], pad=8)
                            except Exception as exc:
                                print(f"        could not walk this filesystem: {exc}")
                        if zf is not None:
                            vol = vol_names.get(b) or f"lba{b // SECTOR}"
                            print(f"        EXTRACTING to {extract}  as {vol}/")
                            try:
                                ents = collect(w, w.root)
                                ents, dropped = apply_exclude(ents, exclude)
                                log = []
                                f_, wr, sk, fa = extract_to_zip(zf, w, vol, ents,
                                                                log, reporter)
                                if manifest is not None:
                                    manifest.append({
                                        "volume": vol, "image": os.path.basename(path),
                                        "lba": b // SECTOR, "offset_bytes": b,
                                        "partition_size_bytes": sz,
                                        "filesystem": "qnx_ifs",
                                        "compression": w.compress,
                                        "imagefs_size_bytes": w.decompressed,
                                        "image_checksum_balances": w.cksum_ok,
                                        "files": f_, "bytes": wr,
                                        "symlinks_or_special_skipped": sk,
                                        "failed": fa, "excluded": dropped,
                                    })
                                print(f"            {f_:,} files, {human(wr)}"
                                      + (f", {sk:,} symlinks or special files skipped"
                                         if sk else "")
                                      + (f", {fa:,} FAILED" if fa else "")
                                      + (f", {dropped:,} excluded" if dropped else ""))
                                for line in log[:5]:
                                    print(line)
                            except Exception as exc:
                                print(f"        could not extract: {exc}")
                print()

        if rejected:
            print(f"  rejected (magic present, fields inconsistent):")
            for off, how, endian, sb, bad in rejected[:6]:
                print(f"    0x{off:<10x} {how:<28} {bad[0]}")
            if len(rejected) > 6:
                print(f"    ... and {len(rejected)-6} more")
            print()

        if do_triage:
            print_triage(triage)

        if confirmed:
            print("  VERDICT: QNX6 filesystem present.")
        elif candidates:
            print("  VERDICT: magic bytes seen but no valid superblock. Not QNX6"
                  " on this evidence.")
        else:
            print("  VERDICT: no QNX6 superblock found.")
    print()


def self_test():
    """Prove the detector reports BOTH ways before you trust a run.

    Builds three throwaway images in a temp directory, checks them, and removes
    the directory. Nothing outside that directory is touched.
    """
    import tempfile, shutil

    # These two literals are deliberately NOT QNX6_MAGIC. A self-test that
    # builds its fixtures from the constant it is verifying is circular: it
    # passes even when the constant is wrong. Measured 2026-08-26, an earlier
    # version of this function passed with QNX6_MAGIC set to 0x68191123.
    # If you change these, change them to the value in
    # linux/include/uapi/linux/magic.h and nowhere else.
    TRUE_MAGIC_LE = b"\x22\x11\x19\x68"   # 0x68191122, little endian on disk
    TRUE_MAGIC_BE = b"\x68\x19\x11\x22"   # 0x68191122, big endian on disk

    d = tempfile.mkdtemp(prefix="qnxprobe_selftest_")
    try:
        ok = True
        if struct.pack("<I", QNX6_MAGIC) != TRUE_MAGIC_LE:
            print(f"  [FAIL] QNX6_MAGIC is 0x{QNX6_MAGIC:08x}, expected 0x68191122")
            print("\n  SELF-TEST FAILED. Do not trust results from this build.")
            return 1

        # positive 1: MBR, little endian, superblock at partition + 0x2000,
        # with fully consistent fields
        img = bytearray(SECTOR * 2048 + 6 * 1024 * 1024)
        ent = bytearray(16)
        ent[4] = 0xb1
        struct.pack_into("<II", ent, 8, 2048, 8192)
        img[446:462] = ent
        img[510:512] = b"\x55\xaa"
        o = 2048 * SECTOR + BOOTBLOCK_SIZE
        img[o:o + 4] = TRUE_MAGIC_LE
        struct.pack_into("<I", img, o + 16, 1521471625)   # ctime 2018-03-19
        struct.pack_into("<I", img, o + 20, 1712222868)   # atime 2024-04-04
        struct.pack_into("<H", img, o + 28, 4)
        struct.pack_into("<H", img, o + 30, 3)
        struct.pack_into("<I", img, o + 48, 4096)         # blocksize
        struct.pack_into("<I", img, o + 52, 20000)        # num_inodes
        struct.pack_into("<I", img, o + 56, 15000)        # free_inodes
        struct.pack_into("<I", img, o + 60, 1020)         # num_blocks
        struct.pack_into("<I", img, o + 64, 966)          # free_blocks
        a = os.path.join(d, "positive_le.img")
        open(a, "wb").write(img)

        # positive 2: no partition table, big endian, superblock at offset 0
        img2 = bytearray(64 * 1024)
        img2[0:4] = TRUE_MAGIC_BE
        struct.pack_into(">I", img2, 16, 1521471625)
        struct.pack_into(">I", img2, 20, 1712222868)
        struct.pack_into(">I", img2, 48, 4096)
        struct.pack_into(">I", img2, 52, 128)
        struct.pack_into(">I", img2, 56, 101)
        struct.pack_into(">I", img2, 60, 1020)
        struct.pack_into(">I", img2, 64, 966)
        b = os.path.join(d, "positive_be.img")
        open(b, "wb").write(img2)

        # negative: deterministic bytes that provably do not contain the magic
        neg = bytes(((i * 7 + 13) & 0xFF) for i in range(2 * 1024 * 1024))
        assert TRUE_MAGIC_LE not in neg and TRUE_MAGIC_BE not in neg
        c = os.path.join(d, "negative.img")
        open(c, "wb").write(neg)

        for path, want, label in ((a, True,  "positive, little endian, MBR +0x2000"),
                                  (b, True,  "positive, big endian, no MBR, +0"),
                                  (c, False, "negative, no magic anywhere")):
            with open(path, "rb") as fh:
                hit = None
                for base in (0, 2048 * SECTOR):
                    for rel in (BOOTBLOCK_SIZE, 0):
                        r = check(fh, base + rel)
                        if r and not r[2]:
                            hit = r
                            break
                    if hit:
                        break
            got = hit is not None
            mark = "PASS" if got == want else "FAIL"
            if got != want:
                ok = False
            print(f"  [{mark}] {label}: detected={got}, expected={want}")

        # FAT and exFAT detection, both ways, from synthetic boot sectors. The
        # type strings are written as literals here, deliberately not by
        # reference to identify_fat's own comparisons, for the same circularity
        # reason as TRUE_MAGIC_LE above: Microsoft's specifications spell them
        # "FAT32   " at offset 82 and "EXFAT   " at offset 3.
        fat = bytearray(64 * 1024)
        fat[82:90] = b"FAT32   "
        struct.pack_into("<H", fat, 11, 512); fat[13] = 1
        struct.pack_into("<I", fat, 32, 96)
        fat[510:512] = b"\x55\xaa"
        fp = os.path.join(d, "fat32.img"); open(fp, "wb").write(fat)

        exf = bytearray(64 * 1024)
        exf[3:11] = b"EXFAT   "
        exf[108] = 9; exf[109] = 0
        struct.pack_into("<Q", exf, 72, 128)
        struct.pack_into("<I", exf, 92, 16)
        exf[510:512] = b"\x55\xaa"
        xp = os.path.join(d, "exfat.img"); open(xp, "wb").write(exf)

        for path, want_kind, label in (
                (fp, "fat32", "fat32 boot sector recognised"),
                (xp, "exfat", "exfat boot sector recognised"),
                (c, None, "no filesystem claimed on the empty image")):
            with open(path, "rb") as fh:
                r = identify_fat(fh, 0)
            got = r[0] if r else None
            mark = "PASS" if got == want_kind else "FAIL"
            if got != want_kind:
                ok = False
            print(f"  [{mark}] {label}: got={got}")

        # A FAT boot sector must not parse as an MBR: its boot code sits where
        # partition entries would be and yields nonsense regions otherwise.
        for path, label in ((fp, "fat32"), (xp, "exfat")):
            with open(path, "rb") as fh:
                r = parse_mbr(fh)
            mark = "PASS" if r is None else "FAIL"
            if r is not None:
                ok = False
            print(f"  [{mark}] parse_mbr declines the {label} boot sector")

        # ETFS and EFS, the QNX flash filesystems. The reserved names and the
        # F3S signature are spelled here as independent literals, deliberately
        # NOT read from ETFS_RESERVED or EFS_SIG, for the same circularity
        # reason as TRUE_MAGIC_LE above: a fixture built from the constant under
        # test cannot go red when that constant is wrong. Break a name or the
        # signature and this self-test exits 1. Change these only to the values
        # in QNX's fs/etfs.h and fs/f3s_spec.h.
        TRUE_RESERVED = {1: ".filetable", 2: ".badblks", 3: ".counts",
                         4: ".lost+found", 5: ".reserved"}
        TRUE_F3S_SIG = b"QSSL_F3S"
        if ETFS_RESERVED != TRUE_RESERVED:
            print(f"  [FAIL] ETFS_RESERVED {ETFS_RESERVED} != {TRUE_RESERVED}")
            ok = False
        if EFS_SIG != TRUE_F3S_SIG:
            print(f"  [FAIL] EFS_SIG {EFS_SIG!r} != {TRUE_F3S_SIG!r}")
            ok = False

        # A synthetic ETFS image: 1024-byte pages, each with a 16-byte spare
        # transaction. One .filetable page (fid 1) carries the reserved entries
        # and a test file at fid 6; a second page carries that file's data.
        Pz = 1024

        def _tr(fid, cluster, seq):               # an "ok" transaction record
            return struct.pack("<IIHBBI", fid, cluster, 1, 0, 0, seq)

        def _fe(pfid, mode, mtime, size, name):    # a 64-byte file-table entry
            return (struct.pack("<HH", 0x0000, pfid)
                    + struct.pack("<7I", mode, 0, 0, 0, mtime, 0, size)
                    + name.encode("utf-8")[:32].ljust(32, b"\x00"))

        payload = b"ETFS self-test payload\n"
        ftbl = bytearray()
        ftbl += _fe(0x0000, S_IFDIR | 0o755, 0, 0, "")                # fid 0 root
        for fid in range(1, 6):
            m = (S_IFDIR | 0o755) if fid == 4 else 0o100444
            ftbl += _fe(0x0000, m, 0, 0, TRUE_RESERVED[fid])          # fids 1..5
        ftbl += _fe(0x0000, 0o100644, 1712000000, len(payload), "selftest.txt")
        ftbl += b"\xff" * (Pz - len(ftbl))         # remaining entries invalid
        etfs_img = (bytes(ftbl) + _tr(ETFS_FID_FTABLE, 0, 5)
                    + payload.ljust(Pz, b"\x00") + _tr(6, 0, 6))
        ep = os.path.join(d, "etfs.bin"); open(ep, "wb").write(etfs_img)

        with open(ep, "rb") as fh:
            det = identify_etfs(fh, 0, len(etfs_img))
            kind = det[0] if det else None
            got = b""
            if kind == "etfs":
                w = walker_for("etfs", fh, 0, len(etfs_img))
                kids = dict(w.listdir(w.root))
                node = kids.get("selftest.txt")
                if node is not None:
                    got = b"".join(w.read_file(node, w.entry(node)[1]))
        mark = "PASS" if (kind == "etfs" and got == payload) else "FAIL"
        if kind != "etfs" or got != payload:
            ok = False
        print(f"  [{mark}] synthetic ETFS recognised and one file round-tripped: "
              f"kind={kind}")

        # A synthetic EFS image: one erase unit whose unit_info sizes it and
        # whose boot record carries the QSSL_F3S signature. Detection only, the
        # same depth as the FAT legs above; the full walk is proven by the
        # round-trip against qnxmount's committed images.
        us_pow2 = 16
        efs_img = bytearray(b"\xff" * (1 << us_pow2))
        struct.pack_into("<H", efs_img, 0, 0x10)          # unit_info struct_size
        efs_img[2] = 0x00                                 # endian
        efs_img[3] = 0xFF                                 # pad
        struct.pack_into("<H", efs_img, 4, us_pow2)       # unit_pow2
        efs_img[6:8] = b"\xff\xff"                        # reserve
        struct.pack_into("<I", efs_img, 8, 0)             # erase_count
        bo = 0x100                                        # boot_info offset
        struct.pack_into("<HBB", efs_img, bo, 0x18, 3, 0)
        efs_img[bo + 4:bo + 12] = TRUE_F3S_SIG
        struct.pack_into("<HHHH", efs_img, bo + 12, 0, 1, 0, 2)   # idx,total,spare,align
        struct.pack_into("<HH", efs_img, bo + 20, 1, 0)          # root ptr
        efp = os.path.join(d, "efs.bin"); open(efp, "wb").write(bytes(efs_img))
        with open(efp, "rb") as fh:
            det = identify_efs(fh, 0, len(efs_img))
        got_kind = det[0] if det else None
        mark = "PASS" if got_kind == "efs" else "FAIL"
        if got_kind != "efs":
            ok = False
        print(f"  [{mark}] synthetic EFS boot record recognised: kind={got_kind}")

        # Neither flash detector may fire on data that is not its filesystem.
        for path, label in ((c, "random"), (fp, "fat32"), (xp, "exfat")):
            sz = os.path.getsize(path)
            with open(path, "rb") as fh:
                e1 = identify_etfs(fh, 0, sz)
                e2 = identify_efs(fh, 0, sz)
            mark = "PASS" if (e1 is None and e2 is None) else "FAIL"
            if e1 is not None or e2 is not None:
                ok = False
            print(f"  [{mark}] ETFS and EFS decline the {label} image")

        # QNX IFS. The UCL decompressor and the imagefs layout are proven byte
        # for byte against real Ford Sync G4 images; these legs are the both-ways
        # regression guard, built from synthetic bytes so no evidence travels.
        #
        # The UCL stream below is a fixed synthetic block that exercises a literal
        # run, a back reference, a reuse of the last offset, a gamma-coded length
        # and the end marker. The expected output is written out by hand rather
        # than taken from the decoder, so a regression fails against a fixed
        # target instead of against itself. It reads: literals "abcXYZ", copy 3
        # from 6 back ("abc"), then copy 7 from 6 back ("XYZabcX").
        UCL_BLOCK = bytes.fromhex("fd61626358595ac40510000000000048ff")
        UCL_WANT = b"abcXYZabcXYZabcX"
        try:
            got = ucl_nrv2b_decompress(UCL_BLOCK)
        except Exception:
            got = None
        mark = "PASS" if got == UCL_WANT else "FAIL"
        if got != UCL_WANT:
            ok = False
        print(f"  [{mark}] UCL NRV2B decompresses a known block to {got!r}")

        broken = bytearray(UCL_BLOCK); broken[1] ^= 0xFF
        try:
            bad = ucl_nrv2b_decompress(bytes(broken))
        except Exception:
            bad = None
        mark = "PASS" if bad != UCL_WANT else "FAIL"
        if bad == UCL_WANT:
            ok = False
        print(f"  [{mark}] a corrupted UCL block does not reproduce it")

        framed = (struct.pack(">H", len(UCL_BLOCK)) + UCL_BLOCK) * 2 + b"\x00\x00"
        try:
            got = ifs_decompress_blocks(framed, ucl_nrv2b_decompress)
        except Exception:
            got = None
        mark = "PASS" if got == UCL_WANT * 2 else "FAIL"
        if got != UCL_WANT * 2:
            ok = False
        print(f"  [{mark}] block framing concatenates two blocks and stops at 0")

        # A small uncompressed imagefs: root dir, a top-level file, a file in an
        # implicit subdirectory, and a symlink. Built from the image.h structs so
        # the walker's dirent parse, implicit-directory synthesis, file read and
        # trailer checksum are all exercised. The trailer is set over the clean
        # image; the sabotaged copy flips one data byte afterwards, so its stored
        # checksum can no longer balance.
        def _ifs_image(corrupt=False):
            f2, f1, tgt = b"second file\n", b"hello d/f1\n", b"/etc/target"
            def attr(size, ino, mode):
                return struct.pack("<HHIIIII", size, 0, ino, mode, 0, 0, 0x5000)
            def d_dir(p, ino):
                t = p + b"\x00"; return attr(24 + len(t), ino, IFS_S_IFDIR | 0o755) + t
            def d_file(p, ino, off, sz):
                t = struct.pack("<II", off, sz) + p + b"\x00"
                return attr(24 + len(t), ino, IFS_S_IFREG | 0o644) + t
            def d_link(p, target, ino):
                nm = p + b"\x00"; t = nm + target + b"\x00"
                return (attr(24 + 4 + len(t), ino, IFS_S_IFLNK | 0o777)
                        + struct.pack("<HH", len(nm), len(target)) + t)
            def table(o2, o1):
                return (d_dir(b"", 1) + d_file(b"f2", 2, o2, len(f2))
                        + d_file(b"d/f1", 3, o1, len(f1))
                        + d_link(b"d/l1", tgt, 4) + struct.pack("<H", 0))
            dir_off = 92
            hdr_dir = dir_off + len(table(0, 0)) - 2
            data = (dir_off + len(table(0, 0)) + 3) & ~3
            o2, o1 = data, data + len(f2)
            img = bytearray(88)
            img[0:7] = b"imagefs"
            struct.pack_into("<I", img, 16, dir_off)
            img += b"/\x00\x00\x00"
            img += table(o2, o1)
            img += b"\x00" * (o2 - len(img))
            img += f2 + f1
            while len(img) % 4:
                img.append(0)
            struct.pack_into("<I", img, 8, len(img) + 4)
            struct.pack_into("<I", img, 12, hdr_dir)
            body = sum(struct.unpack_from("<%dI" % (len(img) // 4), img, 0))
            img += struct.pack("<I", (-body) & 0xFFFFFFFF)
            if corrupt:
                img[o2 + 1] ^= 0xFF
            hdr = bytearray(256)
            struct.pack_into("<I", hdr, 0, QNX_IFS_SIG)
            struct.pack_into("<H", hdr, 4, 1); hdr[6] = 0x01
            struct.pack_into("<H", hdr, 8, 256)
            struct.pack_into("<H", hdr, 10, 183)
            struct.pack_into("<I", hdr, 32, 512)
            struct.pack_into("<I", hdr, 36, 512 + len(img))
            struct.pack_into("<I", hdr, 44, len(img))
            return bytes(hdr) + b"\x00" * (512 - 256) + bytes(img)

        ip = os.path.join(d, "ifs_ok.img"); open(ip, "wb").write(_ifs_image())
        try:
            with open(ip, "rb") as fh:
                det = identify_ifs(fh, 0)
                w = IfsWalker(fh, 0)
                files = {p: (node, sz) for p, node, sz, _ in collect(w, w.root)}
                f2ok = b"".join(w.read_file(*files.get("f2", (None, 0)))) == b"second file\n"
                f1ok = b"".join(w.read_file(*files.get("d/f1", (None, 0)))) == b"hello d/f1\n"
                good = (det is not None and w.compress == "none" and w.cksum_ok is True
                        and f2ok and f1ok and "d" in w.nodes
                        and w.links.get("d/l1") == "/etc/target")
        except Exception:
            good = False
        mark = "PASS" if good else "FAIL"
        if not good:
            ok = False
        print(f"  [{mark}] synthetic IFS: header, tree, subdir, files, symlink, checksum")

        cp = os.path.join(d, "ifs_bad.img"); open(cp, "wb").write(_ifs_image(corrupt=True))
        try:
            with open(cp, "rb") as fh:
                balanced = IfsWalker(fh, 0).cksum_ok
        except Exception:
            balanced = None
        mark = "PASS" if balanced is False else "FAIL"
        if balanced is not False:
            ok = False
        print(f"  [{mark}] a flipped imagefs byte breaks the image checksum")

        print()
        print("  SELF-TEST PASSED. The detector reports positives and negatives"
              if ok else
              "  SELF-TEST FAILED. Do not trust results from this build.")
        return 0 if ok else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


EPILOG = """\
examples:
  # one image
  qnxprobe.py Dodge.img

  # several at once
  qnxprobe.py *.img *.bin

  # a single partition already carved out
  qnxprobe.py partition2.dd

  # prove the detector works before you trust a negative result
  qnxprobe.py --self-test

  # widen the fallback brute scan for an image with an odd layout
  qnxprobe.py --scan-limit 2048 mmcblk0.img

  # list what is inside every filesystem it finds
  qnxprobe.py --list mmcblk0.img

  # copy the logical files out into a zip, ready for a LEAPP tool
  qnxprobe.py --extract sync_g4.zip mmcblk0.img

  # just one partition, by name or label
  qnxprobe.py --extract storage.zip --only storage mmcblk0.img

  # go deeper, and raise the per-filesystem entry cap
  qnxprobe.py --list --depth 4 --list-max 3000 mmcblk0.img

deciding what to pull first:
  --triage ranks every volume it found by how much each has been written, and
  flags the ones that are not worth your time. It uses only what the probe
  already read: the qnx6 superblock serial is a commit counter, and ext
  exposes mount count and lifetime kilobytes written.

  It also samples filenames and says so when they are encrypted, because a
  volume whose names are encrypted will not yield to any parser without the
  keys. Measured on a 2024 BMW MGU: the busiest volume on the disk, /var/opt,
  is 36% encrypted names in a sample.

  Read the fill percentage alongside the ranking rather than sorting on size.
  On a Ford Sync G4 the 4 MiB manufacturing volume, last in the ranking with
  16 commits, is the one holding the unit's Bluetooth and WiFi addresses,
  serials and TLS keys. Activity finds the user data; it does not measure
  value per byte.

getting the files out, without mounting:
  --extract writes every regular file from every filesystem it identified into
  a zip, which is the shape a LEAPP tool expects. Directories are implied by
  the paths; symlinks and special files are counted and skipped. Entries are
  stamped with the file's own mtime, clamped to 1980 where the stored time
  predates what the zip format can hold.

  This exists because mounting is a Linux-only answer. macOS ships no qnx6
  driver, the WSL2 kernel is built with CONFIG_QNX6FS_FS unset, and the FUSE
  options are Linux-tested. --extract is standard library only, so it behaves
  the same on macOS, Windows and Linux, needs no administrator rights, no loop
  device and no virtual machine, and cannot write to the evidence.

  --only restricts --list and --extract to partitions whose name or label
  contains the text given, which matters because a whole head unit can run to
  tens of gigabytes.

  It refuses to overwrite an existing output file.

listing contents:
  --list walks each filesystem it identified and prints the tree. It handles
  qnx6, ext2/3/4, FAT32, exFAT, the QNX flash filesystems ETFS and EFS, and
  QNX IFS boot images, follows qnx6 long filenames and ext4 extent trees, and
  reads only. --depth sets how far down it goes and --list-max caps the number
  of entries per filesystem so a large volume cannot flood the terminal.

what it reports:
  Every superblock copy it can find, grouped into generations by serial. The
  highest serial is the active one; the generation below it is the previous
  committed state, still on disk. It then diffs the two, so you can see what
  one commit actually changed.

  Measured on a Ford Sync G4 image, a qnx6 filesystem carries FOUR copies, not
  two: the 0x1000 area reserved at 0x2000 holds slots at +0x2000 and +0x2e00,
  and a second reserved area near the end of the volume mirrors both. So the
  previous committed state is usually recoverable.

  A copy whose volume id, blocksize and block count match an already-confirmed
  superblock in the same partition is accepted as another copy of that
  filesystem even if its timestamps look wrong, and the run says how many were
  accepted that way. Recorded identity is a stronger signal than a date: on the
  Sync G4 image the previous generation of dps_os carries ctime 308 and atime 1,
  both unset because the build host had no clock, and a timestamp test alone
  rejects a genuine superblock.

  Time differences between generations are printed in whole units, seconds
  through years. Where one side is an unset placeholder rather than a date the
  difference is NOT a duration, and it is reported as the change it is instead
  of a meaningless span of years.

  After the qnx6 volumes it reports WHAT IS IN THE OTHER PARTITIONS, because a
  partition type byte is a label and not a fact. ext2, ext3 and ext4 are read
  in full: label, last mount point, UUID, creation and mount and write times,
  mount count, usage, lifetime bytes written, and whether the volume was
  cleanly unmounted. QNX IFS boot images report their startup header (version,
  target machine, startup code size, compression method), then the image
  filesystem is decompressed and listed and extracted like any other, with the
  image checksum reported as a decode self-check. The QNX flash filesystems
  ETFS and EFS are recognised too, and listed and extracted in full. Anything
  else is reported as its leading bytes plus any ASCII magic,
  so there is a lead to follow rather than a guess. On a 2024 BMW
  MGU image that turned twelve partitions all marked 0x83 "Linux" into ten
  ext4 volumes, one extended container, and one holding an ipk container with
  a Linux bzImage inside it.

  ETFS and EFS are usually imaged bare, with no partition table, so they arrive
  as the whole image and extract under the lba0 name. ETFS has no superblock, so
  its live state is rebuilt by replaying the transaction records in the spare
  area of every page, keeping the highest sequence number for each block; its
  extraction also carries the internal .filetable, .badblks, .counts and
  .reserved bookkeeping files, which are real entries in the filesystem. EFS is
  found by its QSSL_F3S boot record and walked through its extent chains, each
  file resolved to its current version through the superseding-extent pointers.

  sb_ctime is written once, when the filesystem is made. sb_atime moves when
  the filesystem is COMMITTED, not when a file is read, so do not report it as
  when a person last used the device. serial counts commits and is the better
  measure of how much a volume has been written. Measured across three volumes
  of a Ford Sync G4 image: 15 commits on manufacturing data, 1,713 on the OS,
  411,711 on user storage.

  The field names sb_ctime and sb_atime come from comments in the Linux
  header. QNX does not publish the on-disk superblock layout, so treat the
  names as labels and report what moved rather than what someone did.

what it checks, and where the constants come from:
  QNX6_SUPER_MAGIC   0x68191122   linux/include/uapi/linux/magic.h:55
  QNX6_BOOTBLOCK_SIZE    0x2000   linux/include/linux/qnx6_fs.h:23
  struct qnx6_super_block          linux/include/linux/qnx6_fs.h:94

  fs/qnx6/inode.c reads superblock #1 at +0x2000 from the start of the
  partition and retries at +0 if the magic is wrong. Little endian is tried
  first, then big endian. This tool does the same, for the whole image, for
  every MBR primary, every logical volume in the extended chain, and every
  GPT partition.

  A bare 4-byte magic match is not a finding: expect roughly one by chance
  per 256 MiB scanned. Every candidate is parsed as a superblock and its
  fields checked for consistency before it is reported CONFIRMED.

  For the ext side:
  EXT2_SUPER_MAGIC       0xEF53   linux/include/uapi/linux/magic.h:24
  struct ext4_super_block         linux/fs/ext4/ext4.h
  struct ext4_group_desc          linux/fs/ext4/ext4.h
  struct ext4_inode               linux/fs/ext4/ext4.h
  struct ext4_dir_entry_2         linux/fs/ext4/ext4.h
  EXT4_EXT_MAGIC         0xf30a   linux/fs/ext4/ext4_extents.h

  The ext field offsets were derived from that header and cross-checked
  against its own /*NN*/ offset markers, all fifteen of which agreed, with the
  struct totalling the expected 1024 bytes.

  For QNX IFS boot images:
  STARTUP_HDR_SIGNATURE  0x00ff7eeb   qnx sys/startup.h:88
  STARTUP_HDR_VERSION             1   qnx sys/startup.h:89
  struct startup_header               qnx sys/startup.h, and QNX's own
                                      "The startup header" documentation page,
                                      which lists the same fields in the same
                                      order

  Those field widths sum to 256 bytes, which each image's own header_size
  field confirms. The machine field is documented as an ELF machine type and
  is reported through EM_386 3, EM_ARM 40, EM_X86_64 62 and EM_AARCH64 183
  from linux/include/uapi/linux/elf-em.h. The image filesystem begins at
  startup_size, and stored_size minus startup_size against imagefs_size says
  whether it is stored compressed.

  The image filesystem and its compression come from QNX's own dumpifs and
  sys/image.h. startup_header flags1 carries the method (none, zlib, lzo or
  ucl). A compressed imagefs is a run of blocks, each a 2-byte big-endian
  compressed length then that many bytes, decompressing to at most 64 KiB and
  ending at a zero length. Each ucl block is UCL NRV2B, the _8 variant dumpifs
  links as ucl_nrv2b_decompress_8; it is carried here as a small pure-Python
  decoder ported from Markus Oberhumer's UCL (src/n2b_d.c, src/getbit.h), so
  nothing has to be installed. The decompressed image is walked from its
  image_header and a flat table of image_dirent records: each carries an inode,
  mode, mtime and a full path, and a file points at an offset and size inside
  the image. zlib images are read through the standard library.

  This is proven byte for byte against the Ford Sync G4 ifs_a, ifs_b and
  ifs_recovery volumes. Each decompressed to exactly the imagefs_size its own
  header records, the 32-bit words from the header through the image_trailer
  summed to zero (the trailer holds a checksum), and the extracted files were
  valid, including the AArch64 ELF kernel whose machine matched the startup
  header. That checksum is printed on every run as a decode self-check.

  lzo-compressed images and the Harman Becker HBCIFS container are recognised
  but not read here, since no sample exists to validate a reader against, and a
  big-endian image is declined the same way. In each case the header is still
  reported and the walk is declined out loud. Nothing is invented.

  For the QNX flash filesystems ETFS and EFS:
  struct etfs_trans, the fid scheme, ftable and directory entry layouts, and
  the F3S extent, unit and boot structures are transcribed from the Kaitai
  .ksy specs in NetherlandsForensicInstitute/qnxmount (Apache-2.0), whose ETFS
  spec cross-references QNX's own fs/etfs.h and whose EFS spec fs/f3s_spec.h.
  The Kaitai runtime is not a dependency; only the field layouts are copied,
  into the same hand-written struct style as everything above, so this stays
  standard library only. Both readers were validated by extracting qnxmount's
  own committed test images and comparing every name, mode, owner, timestamp,
  symlink target and byte of file content against the tar archive built from
  the same live filesystem, which qnxmount produced on QNX independently of
  this implementation: ETFS matched 32 of 32 entries and EFS 31 of 31.

  ETFS has no magic number. It is claimed only when the region divides evenly
  into (page + 16)-byte pages AND its .filetable carries the fixed reserved
  names .filetable/.badblks/.counts/.lost+found/.reserved at their fixed file
  ids, so a chance page-count match cannot pass. EFS is claimed by its
  QSSL_F3S boot record with a valid F3S revision. Neither fired on the u-boot,
  boot_fs or ext partitions of the two vehicle images tested.

  --list walks qnx6 through the same block resolution the kernel uses in
  qnx6_block_map(), including multi-level indirect trees and long filenames
  held out of line in the Longfile tree, and walks ext through its extent
  trees. Both are read-only.

note:
  The image is opened read-only and is never written to. The Linux qnx6 driver
  has no write path at all, so mounting a qnx6 volume on Linux cannot alter
  these timestamps either.
"""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        prog="qnxprobe.py",
        description="Read QNX6, ETFS, EFS, ext2/3/4, FAT32 and exFAT "
                    "filesystems, and QNX IFS boot images, out of raw disk "
                    "images: identify each by its own on-disk structure rather "
                    "than trusting a partition type byte, list, and extract to a "
                    "zip with a provenance manifest. No mounting, no admin "
                    "rights, standard library only.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="*",
                    help="disk image, partition image, or raw dump to examine")
    ap.add_argument("--scan-limit", type=int, default=256, metavar="MiB",
                    help="how far to brute scan when no superblock sits at the "
                         "offsets the kernel checks (default: 256)")
    ap.add_argument("--self-test", action="store_true",
                    help="build throwaway positive and negative images, confirm "
                         "the detector reports both ways, then delete them")
    ap.add_argument("--list", action="store_true",
                    help="walk each filesystem found and list its contents "
                         "(qnx6, ext2/3/4, FAT32, exFAT, ETFS and EFS)")
    ap.add_argument("--depth", type=int, default=2, metavar="N",
                    help="how deep to walk with --list (default: 2)")
    ap.add_argument("--list-max", type=int, default=400, metavar="N",
                    help="stop after this many entries per filesystem (default: 400)")
    ap.add_argument("--extract", metavar="OUT.zip",
                    help="copy the logical files out of every filesystem found "
                         "into a zip, ready for a LEAPP tool. No mounting, no "
                         "administrator rights, same on macOS, Windows and Linux")
    ap.add_argument("--exclude", metavar="TEXT", action="append",
                    help="skip any path containing TEXT when extracting. "
                         "Repeatable. Use it to leave out encrypted subtrees "
                         "and bulk payloads that no parser can read")
    ap.add_argument("--only", metavar="TEXT",
                    help="restrict --list and --extract to partitions whose "
                         "name or label contains TEXT")
    ap.add_argument("--triage", action="store_true",
                    help="rank the volumes found by how much each has been "
                         "written, and flag encrypted or bulk ones, so you know "
                         "what to extract first")
    ap.add_argument("--progress", action="store_true",
                    help="while extracting, emit one JSON progress object per line on "
                         "stderr, for a caller driving this as a subprocess. stdout, "
                         "the human readable report, is unchanged")
    ap.add_argument("--version", action="version",
                    version=f"qnxprobe {QNXPROBE_VERSION}")
    args = ap.parse_args()

    if args.self_test:
        print("\nqnxprobe self-test\n")
        sys.exit(self_test())

    if not args.image:
        ap.print_help()
        sys.exit(2)

    missing = [p for p in args.image if not os.path.exists(p)]
    if missing:
        sys.exit("not found: " + ", ".join(missing))

    reporter = ProgressEmitter() if args.progress else None
    manifest = []
    zf = None
    if args.extract:
        if os.path.exists(args.extract):
            sys.exit(f"refusing to overwrite an existing file: {args.extract}")
        zf = zipfile.ZipFile(args.extract, "w", zipfile.ZIP_DEFLATED,
                             allowZip64=True)
    try:
        for p in args.image:
            main(p, scan_limit_mib=args.scan_limit, do_list=args.list,
             list_depth=args.depth, list_max=args.list_max,
                 extract=args.extract, only=args.only, zf=zf,
                 do_triage=args.triage, exclude=args.exclude,
                 reporter=reporter, manifest=manifest)
    finally:
        if zf is not None:
            # The provenance record. For a standalone image the directory names
            # are otherwise the only statement of where a file came from; this
            # ties every volume back to the image by LBA and recorded volume id,
            # so the extraction can be checked against any partition tool
            # without trusting the names.
            if manifest:
                zf.writestr("volumes.json", json.dumps(
                    {"written_by": f"qnxprobe {QNXPROBE_VERSION}",
                     "volumes": manifest}, indent=2) + "\n")
            zf.close()
            print(f"\nwrote {args.extract}  "
                  f"({os.path.getsize(args.extract):,} bytes)")
