#!/usr/bin/env python3
"""Safe, evidence-first inspection of GSI payloads. Does not extract or modify images."""
import argparse, hashlib, json, pathlib, zipfile, tarfile
LIMIT = 8 * 1024**3

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def detect(path):
    p=pathlib.Path(path)
    with p.open("rb") as f:
        head=f.read(64)
        if head[:4]==bytes.fromhex("3aff26ed"): return "android_sparse"
        f.seek(1024)
        if f.read(4)==bytes.fromhex("e2e1f5e0"): return "erofs"
        f.seek(1080)
        if f.read(2)==bytes.fromhex("53ef"): return "ext4"
        f.seek(1024)
        if f.read(4)==bytes.fromhex("1020f5f2"): return "f2fs"
        if head[:6]==b"\xfd7zXZ\x00": return "xz"
        if head[:2]==b"\x1f\x8b": return "gzip"
        if head[:4]==bytes.fromhex("04224d18"): return "lz4"
        if head[:4]==b"PK\x03\x04": return "zip"
        if p.stat().st_size>262:
            f.seek(257)
            if f.read(5)==b"ustar": return "tar"
    return "unknown"

def archive_members(path, kind):
    out=[]
    if kind=="zip":
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                if not i.is_dir(): out.append({"name":i.filename,"size":i.file_size})
    elif kind=="tar":
        with tarfile.open(path,"r:*") as t:
            for i in t.getmembers():
                if i.isfile(): out.append({"name":i.name,"size":i.size})
    return out[:2000]

def analyze(path, limit=LIMIT):
    p=pathlib.Path(path)
    if not p.is_file(): raise ValueError("input is not a regular file")
    size=p.stat().st_size
    if size<=0 or size>limit: raise ValueError("file size outside permitted range")
    kind=detect(p)
    members=archive_members(p,kind) if kind in ("zip","tar") else []
    candidates=[m for m in members if pathlib.PurePosixPath(m["name"]).name.lower() in
                ("system.img","system.img.xz","system.img.gz","system.img.lz4")]
    return {"file":p.name,"size_bytes":size,"sha256":sha256(p),"type":kind,
            "archive_members":members,"system_image_candidates":candidates,
            "filesystem":"detected" if kind in ("ext4","erofs","f2fs") else "not_detected",
            "compatibility":"not_assessed","modifications":"none","device_boot_test":"not_performed"}

def markdown(r):
    lines=["# GSI intake report","",f"- File: \`{r['file']}\`",
           f"- Size: {r['size_bytes']} bytes",f"- SHA-256: \`{r['sha256']}\`",
           f"- Payload type: **{r['type']}**",f"- Compatibility: **not assessed**",
           "- This intake stage does not modify or extract the input.",""]
    if r["system_image_candidates"]:
        lines += ["## Candidate system images",""]+[f"- \`{m['name']}\` ({m['size']} bytes)" for m in r["system_image_candidates"]]
    if r["archive_members"]:
        lines += ["","## Archive inventory (up to 2000 files)",""]+[f"- \`{m['name']}\` ({m['size']} bytes)" for m in r["archive_members"]]
    lines += ["","## Next stage","", "Extraction, filesystem editing, repacking and device validation are separate stages and have not been performed."]
    return "\\n".join(lines)+"\\n"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("--out-dir",default="report")
    args=ap.parse_args()
    r=analyze(args.input)
    d=pathlib.Path(args.out_dir); d.mkdir(parents=True,exist_ok=True)
    (d/"gsi-report.json").write_text(json.dumps(r,indent=2)+"\\n")
    (d/"gsi-report.md").write_text(markdown(r))
    print(json.dumps(r,indent=2))
