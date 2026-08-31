"""
This module provides functionality to search and extract files from various
extraction sources.
It handles file pattern matching, copying files to a data folder, extracting
metadata (creation/modification dates), and decrypting encrypted iTunes backups.

Classes:
    FileInfo: Container for file metadata (source path, creation date, modification date)
    FileSeekerBase: Abstract base class for file searching implementations
    FileSeekerDir: File seeker for local directories
    FileSeekerItunes: NOT HERE
    FileSeekerTar: File seeker for TAR/TAR.GZ archives
    FileSeekerZip: File seeker for ZIP archives
    FileSeekerFile: File seeker for individual files

Functions:
    get_itunes_backup_type: Determines iTunes backup type (db/mbdb)
    get_itunes_backup_encryption: Checks if iTunes backup is encrypted
    check_itunes_backup_status: Validates iTunes backup status and encryption
    decrypt_itunes_backup: Decrypts encrypted iTunes backups using provided passcode
"""

import time as timex
import json
import os
import shutil
import subprocess
import sys
import tarfile
import struct
import tempfile

from pathlib import Path
from scripts.ilapfuncs import *
from shutil import copy2, copyfileobj
from zipfile import ZipFile
from fnmatch import _compile_pattern
from functools import lru_cache
normcase = lru_cache(maxsize=None)(os.path.normcase)

def _probe_volume_case_insensitive(folder):
    """True when this folder's volume folds case.

    os.path.normcase reports the platform convention, not the volume.
    Probe by creating Aa then exclusively creating aA.
    """
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return os.path.normcase("Aa") == os.path.normcase("aA")
    probe_a = os.path.join(folder, ".leapp_case_probe_Aa")
    probe_b = os.path.join(folder, ".leapp_case_probe_aA")
    for leftover in (probe_a, probe_b):
        try:
            os.remove(leftover)
        except OSError:
            pass
    wrote_a = False
    wrote_b = False
    try:
        fd = os.open(probe_a, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, b"Aa")
        os.close(fd)
        wrote_a = True
        try:
            fd = os.open(probe_b, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, b"aA")
            os.close(fd)
            wrote_b = True
            return False
        except FileExistsError:
            return True
        except OSError:
            return os.path.normcase("Aa") == os.path.normcase("aA")
    except OSError:
        return os.path.normcase("Aa") == os.path.normcase("aA")
    finally:
        if wrote_a:
            try:
                os.remove(probe_a)
            except OSError:
                pass
        if wrote_b:
            try:
                os.remove(probe_b)
            except OSError:
                pass


def _dest_claim_key(data_path, folds_case):
    normalized = os.path.normpath(data_path)
    return normalized.casefold() if folds_case else normalized


def _case_variant_digest(hash_source):
    """Hex tag for a case-variant copy, derived from the source path.

    Hash the evidence-relative spelling, case preserved, separators normalized,
    so the same source maps to the same tag on every search, every run and
    every machine, and each case variant gets its own tag.
    """
    normalized = str(hash_source).replace('\\', '/').lstrip('/')
    return hashlib.sha256(normalized.encode('utf-8', 'surrogatepass')).hexdigest()


def _case_variant_candidates(root, ext, digest):
    """Candidate alternate names: short tag, full digest, then a counter tail.

    The later tiers only matter when a candidate name is already taken, for
    example by an evidence file that legitimately carries the tagged name. The
    walk over them stays finite because every blocker is a recorded claim or an
    existing file, and both sets are finite.
    """
    yield f"{root}~case-{digest[:8]}{ext}"
    yield f"{root}~case-{digest}{ext}"
    n = 2
    while True:
        yield f"{root}~case-{digest}-{n}{ext}"
        n += 1


def _disambiguated_data_path(data_path, source_key, dest_claims, folds_case,
                             hash_source=None):
    """Pick a dest that does not overwrite a different source.

    When the wanted destination is already claimed by a different source (two
    evidence paths differing only in case fold together on a case-insensitive
    report volume), the copy is written to name~case-<tag>.ext instead. The tag
    names the source rather than the arrival order, so re-searches and repeat
    runs land on the same path with nothing to remember.
    """
    key = _dest_claim_key(data_path, folds_case)
    claimed = dest_claims.get(key)
    if claimed is not None:
        claimed_source, claimed_path = claimed
        if claimed_source == source_key:
            return claimed_path
    elif not os.path.lexists(data_path):
        dest_claims[key] = (source_key, data_path)
        return data_path
    root, ext = os.path.splitext(data_path)
    digest = _case_variant_digest(source_key if hash_source is None else hash_source)
    for alt in _case_variant_candidates(root, ext, digest):
        alt_key = _dest_claim_key(alt, folds_case)
        claimed = dest_claims.get(alt_key)
        if claimed is not None:
            if claimed[0] == source_key:
                return claimed[1]
            continue
        if os.path.lexists(alt):
            continue
        dest_claims[alt_key] = (source_key, alt)
        logfunc(
            f"INFO: destination {data_path} already holds a different source; "
            f"writing {source_key} to {alt}"
        )
        return alt


class FileInfo:
    """
    A class to store file metadata information.
    Attributes:
        source_path (str): The full path to the source file.
        creation_date (datetime): The date and time when the file was created.
        modification_date (datetime): The date and time when the file was last modified.
    """

    def __init__(self, source_path, creation_date, modification_date):
        self.source_path = source_path
        self.creation_date = creation_date
        self.modification_date = modification_date


class FileSeekerBase:
    """
    Abstract base class for file seeking operations.
    This class provides an interface for searching files and performing cleanup operations
    in different storage contexts (e.g., filesystem, archives, databases).
    """
    def search(self, filepattern, return_on_first_hit=False):
        '''Returns a list of paths for files/folders that matched'''
        raise NotImplementedError

    def __init__(self):
        # Refined by _init_dest_guard once the subclass knows its data folder;
        # the defaults leave the dest-guard a pass-through.
        self._dest_claims = {}
        self._data_folder_folds_case = False

    def cleanup(self):
        '''close any open handles'''

    def _init_dest_guard(self, data_folder):
        self._dest_claims = {}
        self._data_folder_folds_case = _probe_volume_case_insensitive(data_folder)

    def _unique_data_path(self, data_path, source_key, hash_source=None):
        return _disambiguated_data_path(
            data_path, source_key, self._dest_claims,
            self._data_folder_folds_case, hash_source=hash_source
        )


class FileSeekerDir(FileSeekerBase):
    """
    This class extends FileSeekerBase to provide functionality for searching files
    within a directory structure, copying matched files to a destination folder,
    and caching search results for performance.
    Attributes:
        directory (str): The root directory to search within.
        data_folder (str): The destination folder where matched files will be copied.
        _all_files (list): Internal list containing all file paths found in the directory tree.
        searched (dict): Cache of search results, mapping file patterns to lists of matched paths.
        copied (dict): Mapping of source file paths to their copied destination paths.
        file_infos (dict): Dictionary storing FileInfo objects with metadata for copied files.
    Methods:
        build_files_list(directory): Recursively scans directory and populates _all_files list.
        search(filepattern, return_on_first_hit=False, force=False): Searches for files matching
            the given pattern, copies them to data_folder, and returns matching paths.
    """

    def __init__(self, directory, data_folder):
        FileSeekerBase.__init__(self)
        self.directory = directory
        self._all_files = []
        self.data_folder = data_folder
        logfunc('Building files listing...')
        self.build_files_list(directory)
        logfunc(f'File listing complete - {len(self._all_files)} files')
        self.searched = {}
        self.copied = {}
        self.file_infos = {}
        self._init_dest_guard(self.data_folder)

    def build_files_list(self, directory):
        '''Populates all paths in directory into _all_files'''
        try:
            files_list = os.scandir(directory)
            for item in files_list:
                self._all_files.append(item.path)
                if item.is_dir(follow_symlinks=False):
                    self.build_files_list(item.path)
        except OSError as ex:
            logfunc(f'Error reading {directory} ' + str(ex))

    def search(self, filepattern, return_on_first_hit=False, force=False):
        if filepattern in self.searched and not force:
            pathlist = self.searched[filepattern]
            return self.searched[filepattern][0] if return_on_first_hit and pathlist else pathlist
        pathlist = []
        pat = _compile_pattern(normcase(filepattern))
        root = normcase("root/")
        for item in self._all_files:
            if pat(root + normcase(item)) is not None:
                item_rel_path = item.replace(self.directory, '')
                data_path = os.path.join(self.data_folder, item_rel_path[1:])
                if is_platform_windows():
                    data_path = data_path.replace('/', '\\')
                if item not in self.copied or force:
                    try:
                        if os.path.isdir(item):
                            pass
                        elif os.path.isfile(item):
                            data_path = self._unique_data_path(
                                data_path, item, hash_source=item_rel_path)
                            os.makedirs(os.path.dirname(data_path), exist_ok=True)
                            copy2(item, data_path)
                            self.copied[item] = data_path
                            creation_date = Path(item).stat().st_ctime
                            modification_date = Path(item).stat().st_mtime
                            file_info = FileInfo(item, creation_date, modification_date)
                            self.file_infos[data_path] = file_info
                        else:
                            logfunc(f"INFO: Item '{item}' is neither a file nor a directory "
                                    "(e.g. symlink not followed, or broken). Skipped.")
                    except OSError as ex:
                        logfunc(f'Could not copy {item} to {data_path} ' + str(ex))
                else:
                    data_path = self.copied[item]
                pathlist.append(data_path)
                if return_on_first_hit:
                    self.searched[filepattern] = pathlist
                    return data_path
        self.searched[filepattern] = pathlist
        return pathlist

class FileSeekerTar(FileSeekerBase):
    """
    This is a class that extends FileSeekerBase to facilitate searching and extracting files
    from a tar archive. It supports both gzip and regular tar files.
    Attributes:
        tar_file_path (str): The path to the tar file.
        data_folder (str): The directory where extracted files will be stored.
        is_gzip (bool): Indicates if the tar file is gzipped.
        tar_file (tarfile.TarFile): The opened tar file object.
        searched (dict): A dictionary to keep track of searched file patterns and their results.
        copied (dict): A dictionary to keep track of files that have been copied.
        file_infos (dict): A dictionary to store file information for extracted files.
    Methods:
        __init__(tar_file_path, data_folder):
            Initializes the FileSeekerTar instance with the specified tar file path and data folder.
        search(filepattern, return_on_first_hit=False, force=False):
            Searches for files matching the given pattern in the tar archive and extracts them to the data folder.
            Returns a list of paths to the extracted files or the first hit if specified.
        cleanup():
            Closes the tar file to free up resources.
    """

    def __init__(self, tar_file_path, data_folder):
        FileSeekerBase.__init__(self)
        self.is_gzip = tar_file_path.lower().endswith('gz')
        mode = 'r:gz' if self.is_gzip else 'r'
        self.tar_file = tarfile.open(tar_file_path, mode)
        self.data_folder = data_folder
        self.searched = {}
        self.copied = {}
        self.file_infos = {}
        self._init_dest_guard(self.data_folder)

    def search(self, filepattern, return_on_first_hit=False, force=False):
        if filepattern in self.searched and not force:
            pathlist = self.searched[filepattern]
            return self.searched[filepattern][0] if return_on_first_hit and pathlist else pathlist
        pathlist = []
        pat = _compile_pattern(normcase(filepattern))
        root = normcase("root/")
        for member in self.tar_file.getmembers():
            if pat(root + normcase(member.name)) is not None:
                clean_name = sanitize_file_path(member.name)
                full_path = os.path.join(self.data_folder, Path(clean_name))
                if member.name not in self.copied or force:
                    try:
                        if member.isdir():
                            os.makedirs(full_path, exist_ok=True)
                        else:
                            full_path = self._unique_data_path(str(full_path), member.name)
                            parent_dir = os.path.dirname(full_path)
                            if not os.path.exists(parent_dir):
                                os.makedirs(parent_dir)
                            with open(full_path, "wb") as fout:
                                fout.write(tarfile.ExFileObject(self.tar_file, member).read())
                                fout.close()
                                file_info = FileInfo(member.name, 0, member.mtime)
                                self.file_infos[full_path] = file_info
                                self.copied[member.name] = full_path
                            os.utime(full_path, (member.mtime, member.mtime))
                    except OSError as ex:
                        logfunc(f'Could not write file to filesystem, path was {member.name} ' + str(ex))
                else:
                    full_path = self.copied[member.name]
                pathlist.append(full_path)
                if return_on_first_hit:
                    self.searched[filepattern] = pathlist
                    return full_path
        self.searched[filepattern] = pathlist
        return pathlist

    def cleanup(self):
        self.tar_file.close()


class FileSeekerZip(FileSeekerBase):
    """
    This is a class that extends FileSeekerBase to facilitate searching and extracting files from a ZIP archive.
    Attributes:
        zip_file (ZipFile): The ZIP file object representing the archive.
        name_list (list): A list of file names contained in the ZIP archive.
        data_folder (str): The directory where extracted files will be stored.
        searched (dict): A dictionary to keep track of searched file patterns and their corresponding paths.
        copied (dict): A dictionary to keep track of files that have been extracted and their paths.
        file_infos (dict): A dictionary to store file information such as creation and modification dates.
    Methods:
        __init__(zip_file_path, data_folder):
            Initializes the FileSeekerZip instance with the specified ZIP file path and data folder.
        decode_extended_timestamp(extra_data):
            Decodes the extended timestamp information from the extra data of a file in the ZIP archive.
        search(filepattern, return_on_first_hit=False, force=False):
            Searches for files matching the specified pattern in the ZIP archive and extracts them if found.
        cleanup():
            Closes the ZIP file to free up resources.
    """

    def __init__(self, zip_file_path, data_folder):
        FileSeekerBase.__init__(self)
        self.zip_file = ZipFile(zip_file_path)
        self.name_list = self.zip_file.namelist()
        self.data_folder = data_folder
        self.searched = {}
        self.copied = {}
        self.file_infos = {}
        self._init_dest_guard(self.data_folder)

    def decode_extended_timestamp(self, extra_data):
        """
        Decode extended timestamps from the provided extra data.
        Parameters:
            extra_data (bytes): The byte sequence containing the extended timestamp
                                information.
        Returns:
            tuple: A tuple containing the creation time and modification time as
                   integers. If the timestamps are not found, returns (None, None).
        """

        offset = 0
        length = len(extra_data)

        while offset < length:
            header_id, data_size = struct.unpack_from('<HH', extra_data, offset)
            offset += 4
            if header_id == 0x5455:
                creation_time = modification_time = None
                flags = struct.unpack_from('B', extra_data, offset)[0]
                offset += 1
                if flags & 1:  # Modification time
                    modification_time, = struct.unpack_from('<I', extra_data, offset)
                    offset += 4
                if flags & 4:  # Creation time
                    creation_time, = struct.unpack_from('<I', extra_data, offset)
                    offset += 4
                return creation_time, modification_time
            else:
                offset += data_size
        return None, None

    def search(self, filepattern, return_on_first_hit=False, force=False):
        if filepattern in self.searched and not force:
            pathlist = self.searched[filepattern]
            return self.searched[filepattern][0] if return_on_first_hit and pathlist else pathlist
        pathlist = []
        pat = _compile_pattern(normcase(filepattern))
        root = normcase("root/")
        for member in self.name_list:
            if member.startswith("__MACOSX"):
                continue
            if pat(root + normcase(member)) is not None:
                if member not in self.copied or force:
                    try:
                        if member.endswith('/'):
                            # Case-variant directories fold into one on a
                            # case-insensitive volume; their files disambiguate
                            # individually, so directory members take no guard.
                            extracted_path = self._extract_member(member)
                        else:
                            intended = self._intended_extract_path(member)
                            extracted_path = self._extract_member(
                                member,
                                dest_path=self._unique_data_path(intended, member))
                        f = self.zip_file.getinfo(member)
                        creation_date, modification_date = self.decode_extended_timestamp(f.extra)
                        file_info = FileInfo(member, creation_date, modification_date)
                        self.file_infos[extracted_path] = file_info
                        date_time = f.date_time
                        date_time = timex.mktime(date_time + (0, 0, -1))
                        os.utime(extracted_path, (date_time, date_time))
                        self.copied[member] = extracted_path
                    except OSError as ex:
                        logfunc(f'Could not write file to filesystem, path was {member} ' + str(ex))
                        continue
                else:
                    extracted_path = self.copied[member]
                pathlist.append(extracted_path)
                if return_on_first_hit:
                    self.searched[filepattern] = pathlist
                    return extracted_path
        self.searched[filepattern] = pathlist
        return pathlist

    def _intended_extract_path(self, member):
        clean_member = sanitize_file_path(member)
        parts = [part for part in clean_member.replace('\\', '/').split('/')
                 if part not in ('', '.', '..')]
        if not parts:
            return self.data_folder
        return os.path.join(self.data_folder, *parts)

    def _extract_member(self, member, dest_path=None):
        """Extract one member, sanitizing names ZipFile.extract() cannot write.

        ZipFile.extract() only replaces a fixed set of printable characters
        (:<>|"?*) and only on Windows; ASCII control characters in the stored
        name (present in real iOS extractions, e.g. chronod icon files) reach
        the OS untouched and Windows rejects them with EINVAL. Members whose
        names need sanitizing are written out manually to a cleaned path.

        dest_path, when given, is the already-disambiguated destination so a
        later case-variant member cannot overwrite an earlier one.
        """
        intended = self._intended_extract_path(member)
        if dest_path is None:
            dest_path = intended
        clean_member = sanitize_file_path(member)
        if dest_path == intended and clean_member == member:
            return self.zip_file.extract(member, path=self.data_folder)
        if member.endswith('/'):
            os.makedirs(dest_path, exist_ok=True)
        else:
            parent = os.path.dirname(dest_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with self.zip_file.open(member) as fin, open(dest_path, 'wb') as fout:
                fout.write(fin.read())
        return dest_path

    def cleanup(self):
        self.zip_file.close()


def _format_duration(seconds):
    seconds = int(max(0, seconds))
    return f'{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'


class _RawExtractProgress:
    """Throttled progress lines for a raw image extraction, through logfunc.

    Reading the volumes out of a head unit image runs for minutes with no output
    between "artifact started" and the first row, which reads as a hang. The
    vendored reader emits one JSON object per line on stderr while it works; this
    turns those into a line an examiner can read, at most every `interval`
    seconds.

    The counts are the reader's own and are exact, not estimated: it knows the
    full entry list for a volume before it writes the first file. Percent is
    per volume, because that is what the reader reports and what an examiner
    watching a multi volume image wants to see move. Rate and elapsed are
    cumulative across the run.

    The line is kept short enough to fit the GUI log pane without widening it.
    """

    def __init__(self, interval=10.0, clock=None, log=None):
        self.interval = interval
        self.clock = clock or timex.monotonic
        self.log = log or logfunc
        self.started = self.clock()
        self.last_report = self.started
        self.done_bytes = 0          # completed volumes
        self.volumes = 0

    def update(self, event):
        """One decoded progress object from the reader."""
        volume = event.get('volume', '?')
        files, total_files = event.get('files', 0), event.get('total_files', 0)
        written, total_bytes = event.get('bytes', 0), event.get('total_bytes', 0)
        complete = total_files and files >= total_files
        now = self.clock()
        if not complete and now - self.last_report < self.interval:
            return
        self.last_report = now
        elapsed = now - self.started
        overall = self.done_bytes + written
        parts = [f'Reading volumes: {volume}',
                 f'{files:,}/{total_files:,} files' if total_files else f'{files:,} files']
        if total_bytes:
            parts.append(f'{100.0 * written / total_bytes:.0f}%')
        if elapsed > 0:
            parts.append(f'{overall / elapsed / (1 << 20):.1f} MiB/s')
        parts.append(f'elapsed {_format_duration(elapsed)}')
        if total_bytes and 0 < written < total_bytes and elapsed > 0 and overall > 0:
            remaining = (total_bytes - written) / (overall / elapsed)
            parts.append(f'~{_format_duration(remaining)} left on this volume')
        self.log('  ' + '  '.join(parts))
        if complete:
            self.done_bytes += written
            self.volumes += 1


def _extract_image_volumes(probe, image_path, staged_zip, exclude=None):
    """Run the vendored reader over a raw image, streaming its output to the log.

    -u so the reader's stdout is unbuffered and its report arrives while it
    works rather than in one block at the end. --progress puts machine readable
    progress on stderr; stderr is merged into stdout here and the two are told
    apart by the leading brace, which no report line has, so one stream is read
    and there is no second pipe to deadlock on. The report names the partition
    table, every filesystem confirmed and what was extracted; that belongs in
    the run log, because it is the record of which volumes the rows came from.
    """
    cmd = [sys.executable, '-u', probe, '--progress', '--extract', staged_zip]
    for text in (exclude or ()):
        cmd += ['--exclude', text]
    cmd.append(image_path)

    logfunc(f'Reading volumes out of {os.path.basename(image_path)} with the '
            f'vendored qnxprobe. This is the slow part of a raw image run.')
    progress = _RawExtractProgress()
    tail = []
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        if line.lstrip().startswith('{'):
            try:
                progress.update(json.loads(line))
                continue
            except ValueError:
                pass    # not ours after all, fall through and log it
        logfunc(line)
        tail.append(line)
        del tail[:-20]
    proc.wait()
    if proc.returncode != 0 or not os.path.isfile(staged_zip):
        detail = '\n'.join(tail) or 'no output'
        raise RuntimeError(
            f'qnxprobe could not extract any filesystem from {image_path}. '
            f'Exit {proc.returncode}. Last output:\n{detail}')


class FileSeekerRaw(FileSeekerZip):
    """Read a raw disk image by extracting its volumes to a zip first.

    Vehicle head units run QNX6 and ext filesystems. Neither mounts here without
    administrator rights, and no filesystem type The Sleuth Kit supports can walk
    QNX6 at all, so a raw head unit image is otherwise unreadable by this tool.
    scripts/vendor/qnxprobe.py reads both directly from the image.

    Working out which partitions hold which filesystem, and which superblock
    generation is the current one, happens inside qnxprobe's own command line flow
    rather than behind a callable seam. Reimplementing that here would duplicate
    logic that then drifts from the vendored copy, which is the thing vendoring
    with a hash guard exists to prevent. So this runs the vendored tool to produce
    a zip of the logical files and then behaves exactly like a zip input, which
    keeps every staging and matching decision on the path the zip seeker already
    exercises on every run.

    The zip is written to a temporary directory and removed by cleanup(). An
    examiner who wants to keep it, which is worth doing for a large image because
    the extraction is the slow part, should run the vendored script directly:

        python3 scripts/vendor/qnxprobe.py --extract volumes.zip IMAGE
        python3 vleapp.py -t zip -i volumes.zip -o REPORT
    """

    def __init__(self, image_path, data_folder, exclude=None):
        self._stage_dir = tempfile.mkdtemp(prefix='vleapp_raw_')
        staged_zip = os.path.join(self._stage_dir, 'qnx_volumes.zip')
        probe = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'vendor', 'qnxprobe.py')
        if not os.path.isfile(probe):
            raise FileNotFoundError(
                f'the vendored reader is missing: {probe}. Raw image input needs '
                'scripts/vendor/qnxprobe.py.')

        _extract_image_volumes(probe, image_path, staged_zip, exclude)
        FileSeekerZip.__init__(self, staged_zip, data_folder)

    def cleanup(self):
        FileSeekerZip.cleanup(self)
        shutil.rmtree(getattr(self, '_stage_dir', ''), ignore_errors=True)



class FileSeekerIva(FileSeekerZip):
    """Read a Berla iVe .iVa export directly.

    An .iVa is a ZIP holding another ZIP, which holds the vehicle's source
    files: usually a raw disk image of the head unit plus the file set iVe
    extracted from it, beside Vehicle.json and iVe's own encrypted database.
    The seekers do not descend into nested archives, so before this a .iVa had
    to be unwrapped by hand (admin/scripts/unwrap_berla_iva.py) and the report
    of a direct run was empty.

    This reaches through the nesting itself. When the export carries a raw
    image, that image is read with the vendored qnxprobe, which is the more
    complete route: on the tested export it reaches a volume the vendor's own
    extracted file set does not include. When no raw image is present, the
    extracted file set is used as it stands. Either way Vehicle.json is staged
    at the root so the export's acquisition record is reported alongside the
    vehicle data.

    Everything intermediate lands in a temporary directory and cleanup()
    removes it. The unwrap script remains the way to KEEP the intermediate
    zip, which makes re-runs cheap on a large export.
    """

    SOURCE_FILES_MEMBER = 'DCASourceFilesUpload.zip'

    def __init__(self, iva_path, data_folder, exclude=None):
        self._stage_dir = tempfile.mkdtemp(prefix='vleapp_iva_')
        probe = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'vendor', 'qnxprobe.py')
        if not os.path.isfile(probe):
            raise FileNotFoundError(
                f'the vendored reader is missing: {probe}. .iVa input needs '
                'scripts/vendor/qnxprobe.py.')

        vehicle_json = None
        with ZipFile(iva_path) as outer:
            names = outer.namelist()
            if 'Vehicle.json' in names:
                vehicle_json = outer.read('Vehicle.json')
            else:
                logfunc('This .iVa carries no Vehicle.json, so no acquisition '
                        'record will be reported for it.')
            inner_names = [n for n in names if n.lower().endswith('.zip')]
            if not inner_names:
                raise RuntimeError(
                    f'{os.path.basename(iva_path)} holds no inner zip, so it '
                    'does not look like an iVe export.')
            inner_path = os.path.join(self._stage_dir, 'inner.zip')
            logfunc(f'Unpacking {os.path.basename(iva_path)}: '
                    f'{inner_names[0]} ...')
            with outer.open(inner_names[0]) as src, open(inner_path, 'wb') as dst:
                copyfileobj(src, dst, 16 << 20)

        with ZipFile(inner_path) as inner:
            if self.SOURCE_FILES_MEMBER not in inner.namelist():
                raise RuntimeError(
                    f'{inner_names[0]} carries no {self.SOURCE_FILES_MEMBER}; '
                    'this export does not include the vehicle source files.')
            source_zip = os.path.join(self._stage_dir, self.SOURCE_FILES_MEMBER)
            logfunc(f'Unpacking {self.SOURCE_FILES_MEMBER} ...')
            with inner.open(self.SOURCE_FILES_MEMBER) as src, \
                    open(source_zip, 'wb') as dst:
                copyfileobj(src, dst, 16 << 20)
        os.remove(inner_path)

        with ZipFile(source_zip) as source:
            images = [n for n in source.namelist()
                      if n.startswith('DiskImages/')
                      and n.lower().endswith(('.img', '.bin', '.dd', '.raw'))]
            image_path = None
            if images:
                image_path = os.path.join(self._stage_dir,
                                          os.path.basename(images[0]))
                logfunc(f'The export carries a raw image, {images[0]}; reading '
                        'the vehicle data from the image itself.')
                with source.open(images[0]) as src, open(image_path, 'wb') as dst:
                    copyfileobj(src, dst, 16 << 20)

        staged_zip = os.path.join(self._stage_dir, 'iva_volumes.zip')
        if image_path is not None:
            _extract_image_volumes(probe, image_path, staged_zip, exclude)
            os.remove(image_path)
            os.remove(source_zip)
        else:
            logfunc('The export carries no raw image; using the file set iVe '
                    'extracted.')
            staged_zip = source_zip

        if vehicle_json is not None:
            with ZipFile(staged_zip, 'a') as add:
                add.writestr('Vehicle.json', vehicle_json)

        FileSeekerZip.__init__(self, staged_zip, data_folder)

    def cleanup(self):
        FileSeekerZip.cleanup(self)
        shutil.rmtree(getattr(self, '_stage_dir', ''), ignore_errors=True)

class FileSeekerFile(FileSeekerBase):
    """
    This is a class that extends FileSeekerBase to facilitate searching for and copying a specific file
    based on a provided filename pattern. It validates the input file path and manages the copying of the file to a
    designated data folder while keeping track of searched patterns and copied files.
    Attributes:
        single_file_abs_path (str): The absolute path of the single file to be sought.
        data_folder (str): The folder where the file will be copied.
        single_file_basename (str or None): The basename of the file if valid; otherwise None.
        searched (dict): A dictionary to store previously searched patterns and their results.
        copied (dict): A dictionary to track copied files and their destination paths.
        file_infos (dict): A dictionary to store file information objects for copied files.
    Methods:
        search(filepattern, return_on_first_hit=False, force=False):
            Searches for the file based on the provided filename pattern and copies it
            to the data folder if a match is found.
        cleanup():
            Placeholder method for cleanup operations (currently does nothing).
    """

    def __init__(self, file_path, data_folder):
        FileSeekerBase.__init__(self)
        self.single_file_abs_path = os.path.abspath(file_path)
        self.data_folder = data_folder

        if not os.path.isfile(self.single_file_abs_path):
            logfunc(f"Error: Input path '{file_path}' provided to FileSeekerFile is not a valid file.")
            self.single_file_basename = None
        else:
            self.single_file_basename = os.path.basename(self.single_file_abs_path)

        self.searched = {}
        self.copied = {}
        self.file_infos = {}
        self._init_dest_guard(self.data_folder)

    def search(self, filepattern, return_on_first_hit=False, force=False):
        if not self.single_file_basename:
            return []

        if filepattern in self.searched and not force:
            return self.searched[filepattern]

        pattern_to_match_filename_against = None  # The specific filename pattern to use

        if '/' in filepattern or '\\' in filepattern:  # Original pattern contains path separators
            basename_of_pattern = os.path.basename(filepattern)

            # If the original pattern implied a path, we only proceed if its filename component
            # is NOT an overly generic wildcard.
            # Overly generic wildcards for a filename part of a path: '*', '**', '*.*'
            # These suggest matching 'any file' within that path, which isn't specific enough
            # for FileSeekerFile if the user provided one specific file.
            if basename_of_pattern not in ('*', '**', '*.*'):
                pattern_to_match_filename_against = basename_of_pattern
            else:
                # Log that this pattern is too generic for a single file context if it includes paths
                logfunc(f"FileSeekerFile: Artifact pattern '{filepattern}' contains path separators, AND its filename "
                        f"component ('{basename_of_pattern}') is too generic (e.g., '*', '**', '*.*'). "
                        f"FileSeekerFile will not match its single file ('{self.single_file_basename}') "
                        "against such a broad path-based pattern. No match.")
                self.searched[filepattern] = []
                return []
        else:  # Original pattern does not contain path separators (e.g., "*.json", "myfile.db")
            # This is a direct filename pattern.
            pattern_to_match_filename_against = filepattern

        # This safeguard should ideally not be hit if logic above is correct
        if not pattern_to_match_filename_against:
            # logfunc(f"FileSeekerFile: No effective filename pattern was derived from original '{filepattern}' to "
            #         f"match against basename '{self.single_file_basename}'. No match.")
            self.searched[filepattern] = []
            return []

        pat = _compile_pattern(normcase(pattern_to_match_filename_against))
        found_data_paths = []

        # logfunc("FileSeekerFile: Attempting to match effective filename pattern "
        #         f"'{pattern_to_match_filename_against}' (derived from artifact pattern "
        #         f"'{filepattern}') against actual file basename '{self.single_file_basename}'")

        if pat(normcase(self.single_file_basename)) is not None:
            # Match successful, proceed to copy
            dest_data_path = os.path.join(self.data_folder, self.single_file_basename)
            if is_platform_windows():
                dest_data_path = dest_data_path.replace('/', '\\')

            if self.single_file_abs_path not in self.copied or force:
                try:
                    dest_data_path = self._unique_data_path(
                        dest_data_path, self.single_file_abs_path,
                        hash_source=self.single_file_basename)
                    os.makedirs(
                        os.path.dirname(dest_data_path) or self.data_folder,
                        exist_ok=True,
                    )
                    copy2(self.single_file_abs_path, dest_data_path)
                    self.copied[self.single_file_abs_path] = dest_data_path
                    s = Path(self.single_file_abs_path).stat()
                    file_info_obj = FileInfo(self.single_file_abs_path, s.st_ctime, s.st_mtime)
                    self.file_infos[dest_data_path] = file_info_obj
                    found_data_paths.append(dest_data_path)
                    # logfunc(f"FileSeekerFile: Matched and copied. Dest: {dest_data_path}")
                except OSError as ex:
                    logfunc("FileSeekerFile: Could not copy file "
                            f"{self.single_file_abs_path} to {dest_data_path}: {str(ex)}")
            else:  # Already copied
                copied_dest_path = self.copied.get(self.single_file_abs_path)
                if copied_dest_path:
                    found_data_paths.append(copied_dest_path)
                    # logfunc(f"FileSeekerFile: Matched (already copied). Dest: {copied_dest_path}")
        else:
            logfunc("FileSeekerFile: No match for effective filename pattern "
                    f"'{pattern_to_match_filename_against}' against "
                    f"actual file basename '{self.single_file_basename}'")

        self.searched[filepattern] = found_data_paths
        return found_data_paths

    def cleanup(self):
        pass
