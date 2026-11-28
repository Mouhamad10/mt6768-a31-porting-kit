# Read-only system image extraction

This helper extracts supported raw ext4 or EROFS images into a destination tree without mounting them:
- ext4: `debugfs -R rdump`
- EROFS: `fsck.erofs --extract`

Android sparse images or compression wrappers must first be normalized by the existing intake/extraction stage. Destination must be empty. The helper makes no image writes; extraction metadata/permission/xattr fidelity depends on the backend and should be verified. Do not treat an extracted tree as boot-compatible.

`python3 tools/system_image_extract.py system.img ./extracted-system`
