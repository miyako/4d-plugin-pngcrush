"""Rebuild only proven Pngcrush outputs; retain every packaged sibling."""

import argparse
from pathlib import Path
import re
import shutil
import stat

import repository


PRODUCT = "Pngcrush"
BASE = Path("test/Plugins")
BUNDLE = BASE / (PRODUCT + ".bundle")
RESOURCE_NAMES = (
    "adler32.c", "arm_init.c", "cexcept.h", "compress.c", "crc32.c", "crc32.h",
    "deflate.c", "deflate.h", "filter_msa_intrinsics.c", "filter_neon_intrinsics.c",
    "filter_sse2_intrinsics.c", "gzclose.c", "gzguts.h", "gzlib.c", "gzread.c",
    "gzwrite.c", "infback.c", "inffast.c", "inffast.h", "inffixed.h", "inflate.c",
    "inflate.h", "inftrees.c", "inftrees.h", "intel_init.c", "mips_init.c",
    "png.c", "png.h", "pngconf.h",
    "pngcrush.c", "pngcrush.h", "pngdebug.h", "pngerror.c", "pngget.c", "pnginfo.h",
    "pnglibconf.h", "pngmem.c", "pngpread.c", "pngpriv.h", "pngread.c", "pngrio.c",
    "pngrtran.c", "pngrutil.c", "pngset.c", "pngstruct.h", "pngtrans.c", "pngwio.c",
    "pngwrite.c", "pngwtran.c", "pngwutil.c", "trees.c", "trees.h", "uncompr.c",
    "zconf.h", "zlib.h", "zutil.c", "zutil.h",
)
RESOURCE_PAIRS = tuple(
    (Path(name), BUNDLE / "Contents/Resources" / name)
    for name in ("constants.xlf", "manifest.json")
) + tuple(
    (Path("lib/pngcrush-1.8.11") / name,
     BUNDLE / "Contents/Resources/pngcrush-1.8.11" / name)
    for name in RESOURCE_NAMES
)
FILES = (
    BUNDLE / f"Contents/MacOS/{PRODUCT}", BUNDLE / "Contents/Info.plist",
    BUNDLE / "Contents/Resources/English.lproj/InfoPlist.strings",
    *(destination for _, destination in RESOURCE_PAIRS),
    BUNDLE / "Contents/_CodeSignature/CodeResources",
)
WINDOWS_NAMES = (f"{PRODUCT}.4DX",)
WINDOWS_BINARY = BUNDLE / f"Contents/Windows64/{PRODUCT}.4DX"
DOWNLOADS = tuple(Path("winbuild") / name for name in WINDOWS_NAMES)
XCODE_DATA = Path("build/XCBuildData")
DIRECTORIES = (
    Path("build") / (PRODUCT + ".build"),
    Path("build/Default") / (PRODUCT + ".build"),
    BASE / (PRODUCT + ".build"),
    BASE / "Default" / (PRODUCT + ".build"),
)


def generated(path):
    return (path in set(map(str, (*FILES, WINDOWS_BINARY, *DOWNLOADS)))
            or bool(re.fullmatch(
                r"build/XCBuildData/(?:build\.db(?:-wal|-shm)?|"
                r"[0-9a-f]{32}\.xcbuilddata/.+)", path))
            or any(path.startswith(str(directory) + "/")
                   for directory in DIRECTORIES))


def validate_paths(paths):
    root = Path.cwd().resolve()
    for path in paths:
        for parent in (path, *path.parents):
            if parent == Path("."):
                break
            if repository.is_link(parent):
                raise ValueError(f"Refusing symlink/reparse output: {parent}")
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Output escapes checkout: {path}")
        if path.is_dir():
            for descendant in path.rglob("*"):
                if repository.is_link(descendant):
                    raise ValueError(f"Refusing symlink/reparse output: {descendant}")
                if not (descendant.is_dir() or stat.S_ISREG(descendant.lstat().st_mode)):
                    raise ValueError(f"Refusing nonregular output: {descendant}")


def prepare():
    validate_paths((*FILES, *DIRECTORIES, XCODE_DATA))
    for path in FILES:
        if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f"Expected generated file: {path}")
    for path in DIRECTORIES:
        if path.exists() and not path.is_dir():
            raise ValueError(f"Expected intermediate directory: {path}")
    for path in FILES:
        path.unlink(missing_ok=True)
    for path in DIRECTORIES:
        if path.exists():
            shutil.rmtree(path)


def require_file(path):
    validate_paths((path,))
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing or empty native output: {path}")


def validate_unsigned_outputs():
    validate_paths((*FILES, WINDOWS_BINARY, *DOWNLOADS, *DIRECTORIES, XCODE_DATA))
    for path in FILES[:-1]:
        require_file(path)


def validate_outputs():
    validate_unsigned_outputs()
    require_file(FILES[-1])


def verify_resources():
    for source, copied in RESOURCE_PAIRS:
        require_file(source)
        require_file(copied)
        if copied.read_bytes() != source.read_bytes():
            raise ValueError(f"Copied resource differs from source: {copied}")


def merge_windows():
    validate_paths((*DOWNLOADS, WINDOWS_BINARY))
    for path in DOWNLOADS:
        require_file(path)
    if WINDOWS_BINARY.exists() and not stat.S_ISREG(WINDOWS_BINARY.lstat().st_mode):
        raise ValueError(f"Expected Windows destination file: {WINDOWS_BINARY}")
    WINDOWS_BINARY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DOWNLOADS[0], WINDOWS_BINARY)


def verify_windows():
    for path in (DOWNLOADS[0], WINDOWS_BINARY):
        require_file(path)
    if DOWNLOADS[0].read_bytes() != WINDOWS_BINARY.read_bytes():
        raise ValueError(f"Merged Windows payload differs from downloaded artifact: {WINDOWS_BINARY}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=(
        "clean-macos", "verify-resources", "verify-unsigned", "merge-windows",
    ))
    phase = parser.parse_args().phase
    if phase == "clean-macos":
        prepare()
    elif phase == "merge-windows":
        merge_windows()
    elif phase == "verify-unsigned":
        validate_unsigned_outputs()
    else:
        verify_resources()
