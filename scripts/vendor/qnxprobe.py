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
import os, struct, sys, datetime, json, time, uuid, zipfile

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
# header, the startup code, then the image filesystem, often compressed.
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
# The image filesystem begins at startup_size, and stored_size - startup_size
# against imagefs_size says whether it is stored compressed.
#
# Contents are NOT listed. The IFS directory format is not sourced here, and
# on the images tested the filesystem is compressed, so listing it would mean
# guessing at a layout and decompressing. Reported, not invented.
# ---------------------------------------------------------------------------
QNX_IFS_SIG = 0x00FF7EEB
QNX_IFS_VER = 1
IFS_F = dict(signature=0, version=4, flags1=6, flags2=7, header_size=8,
             machine=10, startup_vaddr=12, paddr_bias=16, image_paddr=20,
             ram_paddr=24, ram_size=28, startup_size=32, stored_size=36,
             imagefs_paddr=40, imagefs_size=44, preboot_size=48)
IFS_HDR_SIZE = 256
ELF_MACHINE = {3: "x86", 40: "ARM 32 bit", 62: "x86-64", 183: "ARM 64 bit"}


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

    lines = [f"version      {ver}" + ("" if ver == QNX_IFS_VER
                                      else f"   (STARTUP_HDR_VERSION is {QNX_IFS_VER})"),
             f"header_size  {hsz}" + ("   agrees with the 256-byte struct"
                                      if hsz == IFS_HDR_SIZE else
                                      "   DOES NOT match the 256-byte struct"),
             f"machine      {mach}  ({ELF_MACHINE.get(mach, 'unrecognised ELF machine')})",
             f"flags        0x{h[IFS_F['flags1']]:02x} 0x{h[IFS_F['flags2']]:02x}"
             f"   startup_vaddr 0x{g32('startup_vaddr'):08x}",
             f"startup      {human(ss)} of startup code, image filesystem begins at "
             f"0x{ss:x}"]

    stored_ifs = st - ss
    if stored_ifs == ifs_sz:
        how = "stored uncompressed"
    elif 0 < stored_ifs < ifs_sz:
        how = f"stored compressed, {human(ifs_sz)} into {human(stored_ifs)}"
    else:
        how = "stored size and imagefs size disagree"
    lines.append(f"imagefs      {human(ifs_sz)} uncompressed, {how}")
    lines.append(f"total        {human(st)} stored on the partition")

    # the image filesystem carries a literal 'imagefs' signature at its head
    near = read_at(fh, base + ss, 64)
    at = near.find(b"imagefs")
    lines.append("imagefs sig  " + (f"found at startup_size + {at}" if at >= 0
                                    else "not found in the 64 bytes at startup_size"))
    lines.append("contents     not listed, the IFS directory format is not "
                 "sourced here (see --help)")
    return lines


def identify_fs(fh, base):
    """Return (name, [detail lines]) for whatever sits at this partition."""
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

    # Not ext, not qnx6, not IFS. Report the leading bytes so there is a lead
    # to follow, rather than inventing a signature for it.
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


def main(path, scan_limit_mib=256, do_list=False, list_depth=2, list_max=400,
         extract=None, only=None, zf=None, do_triage=False, exclude=None,
         reporter=None):
    size = os.path.getsize(path)
    print("=" * 78)
    print(path)
    print(f"  {size:,} bytes ({human(size)})")
    print("=" * 78)

    candidates, regions, sized_regions, triage = [], [], [], []
    containers, protective = set(), set()
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
                if t in (0x05, 0x0f, 0x85):
                    containers.add(f"MBR part {idx}")
                if t == 0xEE:
                    protective.add(f"MBR part {idx}")

        # An extended partition holds the logical volumes; walk the EBR chain,
        # or the largest region of the image is never probed at all.
        EXT = (0x05, 0x0f, 0x85)
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
                vol = key.split()[-1] if key.split() else key
                print(f"\n      EXTRACTING to {extract}")
                try:
                    w = Qnx6Walker(fh, base, sorted(act["at"])[0] - base)
                    ents = collect(w, w.root)
                    ents, dropped = apply_exclude(ents, exclude)
                    log = []
                    f_, wr, sk, fa = extract_to_zip(zf, w, vol, ents, log, reporter)
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
                kind, lines = identify_fs(fh, b)
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
                    vol = ext_name or lab.replace(" ", "_")
                    print(f"        EXTRACTING to {extract}")
                    try:
                        w = ExtWalker(fh, b)
                        ents = collect(w, w.root)
                        ents, dropped = apply_exclude(ents, exclude)
                        log = []
                        f_, wr, sk, fa = extract_to_zip(zf, w, vol, ents, log, reporter)
                        print(f"            {f_:,} files, {human(wr)}"
                              + (f", {sk:,} symlinks or special files skipped" if sk else "")
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
  qnx6 and ext2/3/4, follows qnx6 long filenames and ext4 extent trees, and
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
  cleanly unmounted. QNX IFS boot images are recognised and their startup
  header reported: version, target machine, how much startup code precedes the
  image filesystem, and whether that filesystem is stored compressed. Anything
  else is reported as its leading bytes plus any ASCII magic, so there is a
  lead to follow rather than a guess. On a 2024 BMW
  MGU image that turned twelve partitions all marked 0x83 "Linux" into ten
  ext4 volumes, one extended container, and one holding an ipk container with
  a Linux bzImage inside it.

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

  IFS contents are NOT listed. The IFS directory format is not sourced here,
  and on every image tested the filesystem is stored compressed, so listing it
  would mean guessing a layout and decompressing. The header is reported and
  nothing is invented.

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
        description="Decide whether an extraction holds a QNX6 filesystem, "
                    "by locating and validating the superblock rather than "
                    "trusting a partition type byte.",
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
                         "(qnx6 and ext2/3/4)")
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
    ap.add_argument("--version", action="version", version="qnxprobe 1.4")
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
                 reporter=reporter)
    finally:
        if zf is not None:
            zf.close()
            print(f"\nwrote {args.extract}  "
                  f"({os.path.getsize(args.extract):,} bytes)")
