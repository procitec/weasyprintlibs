#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, os, shutil, subprocess, tarfile, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(cmd, *, cwd=None, env=None):
    print('+', ' '.join(map(str,cmd)), flush=True)
    subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,check=True)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def unpack(archive,dst):
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir(parents=True)
    with tarfile.open(archive,'r:*') as t:
        t.extractall(dst,filter='data')
    children=[p for p in dst.iterdir()]
    return children[0] if len(children)==1 and children[0].is_dir() else dst

def env_for(prefix):
    e=os.environ.copy(); lib=prefix/'lib'; lib64=prefix/'lib64'
    e['PATH']=f'{prefix}/bin:'+e.get('PATH','')
    e['PKG_CONFIG_PATH']=':'.join(str(p) for p in (lib/'pkgconfig',lib64/'pkgconfig',prefix/'share/pkgconfig'))
    e['CMAKE_PREFIX_PATH']=str(prefix)
    e['LD_LIBRARY_PATH']=':'.join([str(lib),str(lib64),e.get('LD_LIBRARY_PATH','')])
    e['ACLOCAL_PATH']=str(prefix/'share/aclocal')
    return e

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--only'); ap.add_argument('--clean',action='store_true'); args=ap.parse_args()
    cfg=tomllib.loads((ROOT/'config/libraries.toml').read_text())
    b=cfg['build']; prefix=ROOT/b['prefix']; sources=ROOT/b['source_dir']; works=ROOT/b['build_dir']
    if args.clean:
        shutil.rmtree(ROOT/'_build',ignore_errors=True)
    prefix.mkdir(parents=True,exist_ok=True); sources.mkdir(parents=True,exist_ok=True); works.mkdir(parents=True,exist_ok=True)
    jobs=b.get('jobs') or os.cpu_count() or 2; e=env_for(prefix)
    for item in cfg['library']:
        if args.only and item['name']!=args.only: continue
        archive=ROOT/b['download_dir']/item['archive']
        if not archive.exists(): raise SystemExit(f'missing source archive: {archive}; run scripts/fetch_sources.py first')
        checksum=item.get('checksum','unlocked')
        if checksum!='unlocked':
            algo, expected=checksum.split(':',1)
            h=hashlib.new(algo)
            with archive.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
            actual=h.hexdigest()
            if actual!=expected: raise SystemExit(f'checksum mismatch: {archive}: {actual}')
        src=unpack(archive,sources/item['name']); src=src/item.get('source_subdir','') if item.get('source_subdir') else src; work=works/item['name']
        shutil.rmtree(work,ignore_errors=True)
        bs=item['build_system']
        if bs=='meson':
            run(['meson','setup',work,src,f'--prefix={prefix}','--libdir=lib','--buildtype=release','--default-library=shared','--wrap-mode=nodownload',*item.get('meson',[])],env=e)
            run(['meson','compile','-C',work,f'-j{jobs}'],env=e); run(['meson','install','-C',work],env=e)
        elif bs=='autotools':
            if item.get('autogen'): run(item['autogen'].split(),cwd=src,env=e)
            work.mkdir(parents=True)
            run([src/'configure',f'--prefix={prefix}',*item.get('configure',[])],cwd=work,env=e)
            run(['make',f'-j{jobs}'],cwd=work,env=e); run(['make','install'],cwd=work,env=e)
        elif bs=='cmake':
            run(['cmake','-S',src,'-B',work,f'-DCMAKE_INSTALL_PREFIX={prefix}','-DCMAKE_BUILD_TYPE=Release',*item.get('cmake',[])],env=e)
            run(['cmake','--build',work,'--parallel',str(jobs)],env=e); run(['cmake','--install',work],env=e)
        else: raise SystemExit(f'unsupported build system: {bs}')
if __name__=='__main__': main()
