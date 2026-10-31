#!/usr/bin/env python3
"""Install reviewed Linux amd64 CI tools with exact SHA256 checksums."""
import hashlib, io, json, os, pathlib, sys, tarfile, urllib.request
pins=json.loads(pathlib.Path(__file__).with_name("tools.json").read_text())
dest=pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp"))/"online-store-ci-bin"
dest.mkdir(parents=True,exist_ok=True)
for name in sys.argv[1:]:
    pin=pins[name]
    data=urllib.request.urlopen(pin["url"],timeout=120).read()
    if hashlib.sha256(data).hexdigest()!=pin["sha256"]:
        raise SystemExit("Checksum mismatch: "+name)
    if name == "cosign":
        target=dest/name
        target.write_bytes(data)
        target.chmod(0o755)
        print(name,pin["version"])
        continue
    with tarfile.open(fileobj=io.BytesIO(data),mode="r:gz") as archive:
        member=next(m for m in archive.getmembers() if m.isfile() and pathlib.PurePosixPath(m.name).name==name)
        target=dest/name
        target.write_bytes(archive.extractfile(member).read())
        target.chmod(0o755)
    print(name,pin["version"])
if os.environ.get("GITHUB_PATH"):
    with open(os.environ["GITHUB_PATH"],"a") as f: f.write(str(dest)+"\n")
else: print("Add to PATH:",dest)
