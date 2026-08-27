# pylint: skip-file
#
# Vendored from CCL Forensics. ArtifactLocationProtocol is defined inline here
# rather than imported from the upstream package, so this repo carries no
# dependency on ccl_chromium_reader being installed.
import typing


class ArtifactLocationProtocol(typing.Protocol):
    @property
    def source_file(self) -> str:
        raise NotImplementedError()

    @property
    def offset(self) -> typing.Optional[int]:
        raise NotImplementedError()

    @property
    def friendly_string(self) -> str:
        raise NotImplementedError()


class ArtifactLocation(ArtifactLocationProtocol):
    def __init__(self, source_file: str, offset: typing.Optional[int], friendly_string: str):
        self._source_file = source_file
        self._offset = offset
        self._friendly_string = friendly_string

    @property
    def source_file(self) -> str:
        return self._source_file

    @property
    def offset(self) -> typing.Optional[int]:
        return self._offset

    @property
    def friendly_string(self) -> str:
        return self._friendly_string

    def __str__(self):
        return self._friendly_string
