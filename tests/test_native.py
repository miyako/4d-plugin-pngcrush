"""Narrow macOS cleanup and final-only output retention."""

import shutil
from pathlib import Path
from unittest import mock

from helper_support import Fixture, GitFixture, ROOT, cwd, original
import native
import repository


class NativePreparationTests(Fixture):
    def test_exact_native_source_resource_topology(self):
        names = {path.name for path in (ROOT / "lib/pngcrush-1.8.11").iterdir()}
        self.assertEqual(len(names), 57)
        self.assertEqual(len(native.RESOURCE_NAMES), 57)
        self.assertEqual(names, set(native.RESOURCE_NAMES))
        self.assertEqual(len(native.RESOURCE_PAIRS), 59)
        for source_path, destination in native.RESOURCE_PAIRS:
            relative = (source_path.relative_to("lib") if str(source_path).startswith("lib/")
                        else source_path)
            self.assertEqual(destination, native.BUNDLE / "Contents/Resources" / relative)
            self.assertEqual(original(source_path), original(destination))

    def test_all_deletion_target_types_prevalidated_before_any_cleanup(self):
        for where in (native.FILES[-1], native.DIRECTORIES[-1]):
            with self.subTest(where=where):
                first = self.write(native.FILES[0], b"must remain")
                path = self.root / where
                path.parent.mkdir(parents=True, exist_ok=True)
                if where in native.FILES:
                    path.mkdir()
                else:
                    path.write_bytes(b"not an intermediate directory")
                with cwd(self.root), self.assertRaisesRegex(ValueError, "Expected"):
                    native.prepare()
                self.assertEqual(first.read_bytes(), b"must remain")
                path.rmdir() if path.is_dir() else path.unlink()

    def test_selective_cleanup_preserves_resources_dependencies_and_default_siblings(self):
        protected = (
            native.BUNDLE / "Contents/QuickLook/Thumbnail.png",
            native.BUNDLE / "Contents/MacOS/runtime.dylib",
            native.BUNDLE / "Contents/Resources/custom.txt",
            native.BASE / "Default/Pngcrush.bundle/Contents/Info.plist",
            native.BASE / "Default/keep", native.BASE / "Other.bundle/keep",
            "build/unrelated/keep", "lib/windows64/jsoncpp.lib", "4DPlugin-Pngcrush.h",
        )
        for path in protected:
            self.write(path, b"preserved")
        for path in native.FILES:
            self.write(path, b"stale")
        for path in native.DIRECTORIES:
            self.write(path / "intermediate", b"stale")
        with cwd(self.root):
            native.prepare()
            native.prepare()
        for path in protected:
            self.assertEqual((self.root / path).read_bytes(), b"preserved")
        for path in (*native.FILES, *native.DIRECTORIES):
            self.assertFalse((self.root / path).exists(), path)

    def test_symlink_anywhere_prevalidated_before_first_deletion(self):
        for where in (native.FILES[-1], native.DIRECTORIES[-1], native.BUNDLE,
                      native.DIRECTORIES[0] / "nested/link"):
            with self.subTest(where=where):
                first = self.write(native.FILES[0], b"must remain")
                destination = self.write("outside/keep", b"untouched")
                link = self.root / where
                if link.is_dir():
                    shutil.rmtree(link)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(destination)
                with cwd(self.root), self.assertRaisesRegex(ValueError, "symlink"):
                    native.prepare()
                if where != native.BUNDLE:
                    self.assertEqual(first.read_bytes(), b"must remain")
                self.assertEqual(destination.read_bytes(), b"untouched")
                link.unlink()

    def test_cleanup_io_error_is_fatal(self):
        self.write(native.FILES[0], b"stale")
        with cwd(self.root), mock.patch("pathlib.Path.unlink", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                native.prepare()
        self.write(native.DIRECTORIES[0] / "stale", b"stale")
        with cwd(self.root), mock.patch("shutil.rmtree", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                native.prepare()

    def test_resources_must_be_fresh_exact_source_copies(self):
        for source_path, destination in native.RESOURCE_PAIRS:
            self.write(source_path, b"source")
            self.write(destination, b"source")
        with cwd(self.root):
            native.verify_resources()
            (native.BUNDLE / "Contents/Resources/constants.xlf").write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError, "differs"):
                native.verify_resources()

    def test_xcode_data_is_not_recursively_cleaned(self):
        paths = (
            "build/XCBuildData/build.db",
            "build/XCBuildData/unexpected-source.cpp",
            "build/XCBuildData/evil.xcbuilddata/keep",
        )
        for path in paths:
            self.write(path, b"preserve original bytes")
        with cwd(self.root):
            native.prepare()
        for path in paths:
            self.assertEqual((self.root / path).read_bytes(), b"preserve original bytes")

    def test_exact_windows_artifact_merge_and_final_revalidation(self):
        for path in native.DOWNLOADS:
            self.write(path, b"fresh binary" if path.suffix == ".4DX" else b"runtime")
        for name in native.WINDOWS_NAMES[1:]:
            self.write(native.BUNDLE / "Contents/Windows64" / name, b"runtime")
        with cwd(self.root):
            native.merge_windows()
            native.verify_windows()
            self.assertEqual(native.WINDOWS_BINARY.read_bytes(), b"fresh binary")
            native.WINDOWS_BINARY.write_bytes(b"late substitution")
            with self.assertRaisesRegex(ValueError, "differs"):
                native.verify_windows()

    def test_final_packaged_output_validation_requires_every_nonempty_regular_leaf(self):
        for path in native.FILES:
            self.write(path, b"fresh output")
        with cwd(self.root):
            native.validate_outputs()
            for path in native.FILES:
                saved = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, "Missing or empty"):
                    native.validate_outputs()
                path.write_bytes(b"")
                with self.assertRaisesRegex(ValueError, "Missing or empty"):
                    native.validate_outputs()
                path.write_bytes(saved)

    def test_unsigned_validation_does_not_require_signature_but_final_validation_does(self):
        for path in native.FILES[:-1]:
            self.write(path, b"fresh unsigned output")
        with cwd(self.root):
            native.validate_unsigned_outputs()
            with self.assertRaisesRegex(ValueError, "Missing or empty"):
                native.validate_outputs()
            native.FILES[-1].parent.mkdir(parents=True, exist_ok=True)
            native.FILES[-1].write_bytes(b"fresh signature")
            native.validate_outputs()


class GeneratedRetentionTests(GitFixture):
    def test_actual_xcode_database_wal_and_outputs_are_final_only(self):
        for relative in (
            *native.FILES,
            "build/XCBuildData/build.db", "build/XCBuildData/build.db-wal",
            "build/XCBuildData/build.db-shm",
            "build/XCBuildData/0123456789abcdef0123456789abcdef.xcbuilddata/build-request.json",
            "build/Pngcrush.build/Default/Pngcrush.build/Objects-normal/arm64/main.o",
            "build/Default/Pngcrush.build/main.o",
        ):
            target = self.local / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fresh native output")
        with cwd(self.local):
            with self.assertRaises(ValueError):
                repository.verify_checkout(self.sha, generated=native.generated)
            repository.verify_checkout(self.sha, generated=native.generated, final=True)

    def test_evil_siblings_and_protected_resource_never_gain_final_exemption(self):
        for relative in (
            "build/XCBuildData-evil/build.db",
            "build/XCBuildData/unexpected-source.cpp",
            "build/XCBuildData/build.db-evil",
            "build/XCBuildData/evil.xcbuilddata/build-request.json",
            "build/Pngcrush.build-evil/main.o",
            "build/unexpected-source.cpp",
            "Objs/Release-evil/main.obj",
            "Objs/Debug/main.obj",
            "winbuild/nested/Pngcrush.4DX",
            "test/Plugins/Default/Pngcrush.bundle/Contents/Info.plist",
            str(native.BUNDLE / "Contents/QuickLook/Thumbnail.png"),
            str(native.BUNDLE / "Contents/MacOS/runtime.dylib"),
            str(native.BUNDLE / "Contents/Resources/custom.txt"),
            str(native.BUNDLE / "Contents/_CodeSignature/evil"),
        ):
            with self.subTest(relative=relative):
                target = self.local / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"unexpected")
                with cwd(self.local), self.assertRaises(ValueError):
                    repository.verify_checkout(self.sha, generated=native.generated, final=True)
                target.unlink()
