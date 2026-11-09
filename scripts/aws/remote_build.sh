#!/usr/bin/env bash
# Runs ON the instance. remote_build.sh <approved_commit> <expected_gzip_sha256> <expected_tar_sha256>
# Rebuilds netspout.spl from the approved source commit, twice (second time from an empty wheel cache and touched files), compares with each other and with the approved hashes.
# The uncompressed-tar hash is reported too: gzip bytes can differ between zlib builds while the content is identical. Whatever is built here is the artifact tested on this host.
set -eu
COMMIT=$1; EXP_GZ=$2; EXP_TAR=$3
W=/opt/p17; PY=$W/venv/bin/python; SRC=$W/approved-src; OUT=$W/harness/docs/verification/evidence/phase17/aws-native-x86_64/build; mkdir -p $OUT
rm -rf $SRC && mkdir -p $SRC && gzip -dc $W/approved-src.tar.gz | tar -x -C $SRC
GOT=$(gzip -dc $W/approved-src.tar.gz | git get-tar-commit-id)
[ "$GOT" = "$COMMIT" ] || { echo "approved source archive is commit $GOT, expected $COMMIT"; exit 2; }
build() { ( cd $SRC && $PY scripts/build_single_package.py --verify > $OUT/build_$1.log 2>&1 && cp build/single_package/netspout.spl $W/build/netspout_$1.spl ); }
build 1
rm -rf $SRC/build/wheel_cache; find $SRC -type f -exec touch -d '2020-01-01' {} +
build 2
G1=$(sha256sum $W/build/netspout_1.spl | cut -d' ' -f1); G2=$(sha256sum $W/build/netspout_2.spl | cut -d' ' -f1)
T1=$(gzip -dc $W/build/netspout_1.spl | sha256sum | cut -d' ' -f1); T2=$(gzip -dc $W/build/netspout_2.spl | sha256sum | cut -d' ' -f1)
cp $W/build/netspout_1.spl $W/build/netspout.spl
$PY - <<PYEOF > $OUT/build_report.json
import json
r = {"approved_commit": "$COMMIT", "build_host_python": "$($PY -V)", "build1_gzip_sha256": "$G1", "build2_gzip_sha256": "$G2", "reproducible_gzip_bytes_on_this_host": "$G1" == "$G2",
     "build1_tar_sha256": "$T1", "build2_tar_sha256": "$T2", "reproducible_tar_content_on_this_host": "$T1" == "$T2",
     "approved_gzip_sha256": "$EXP_GZ", "approved_tar_sha256": "$EXP_TAR", "gzip_matches_approved": "$G1" == "$EXP_GZ", "tar_content_matches_approved": "$T1" == "$EXP_TAR", "bytes": $(stat -c %s $W/build/netspout_1.spl),
     "tested_artifact_sha256": "$G1", "note": "if only the tar content matches, the gzip stream differs (zlib build); the artifact tested here is build 1 and its hash is recorded above"}
print(json.dumps(r, indent=1))
PYEOF
cat $OUT/build_report.json
[ "$G1" = "$G2" ] && [ "$T1" = "$T2" ]
