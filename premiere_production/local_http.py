"""Local HTTP transport adapter for the installed Premiere stdio MCP server.

It forwards JSON-RPC unchanged to the existing server and CEP backend. No Adobe
implementation, extra authority, credential discovery, retries or network bind
beyond IPv4 loopback. Exactly one request is forwarded at a time.
"""
import argparse
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import os
from pathlib import Path
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server-script',type=Path,required=True)
    p.add_argument('--bridge-directory',type=Path,required=True)
    p.add_argument('--token-file',type=Path,required=True)
    p.add_argument('--port',type=int,default=11489)
    args=p.parse_args()
    if not args.server_script.is_file() or not args.bridge_directory.is_dir():raise FileNotFoundError('Existing installed server and CEP directory required')
    token=args.token_file.read_text().strip()
    if not token:raise ValueError('Existing local transport token required')
    env={**os.environ,'PREMIERE_TEMP_DIR':str(args.bridge_directory.resolve()),'PREMIERE_MCP_CAPABILITIES':'inspect,edit,filesystem,export'}
    child=subprocess.Popen(['node',str(args.server_script.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_POST(self):
            if self.path!='/mcp' or self.headers.get('Authorization')!='Bearer '+token:
                self.send_error(403);return
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16*1024**2:self.send_error(413);return
            raw=self.rfile.read(size);request=json.loads(raw)
            child.stdin.write(json.dumps(request,ensure_ascii=False).encode()+b'\n');child.stdin.flush()
            if 'id' not in request:self.send_response(204);self.end_headers();return
            while True:
                line=child.stdout.readline()
                if not line:raise RuntimeError('Installed Premiere MCP process exited; never retry an uncertain operation')
                try:response=json.loads(line)
                except json.JSONDecodeError:continue
                if response.get('id')==request['id']:break
            payload=json.dumps(response,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    server=HTTPServer(('127.0.0.1',args.port),Handler)
    print(json.dumps({'listening':'127.0.0.1:'+str(args.port),'backend':'existing CEP','authority':'inspect,edit,filesystem,export','unsafe_script':False}),flush=True)
    try:server.serve_forever()
    finally:server.server_close();child.terminate();child.wait(timeout=10)


if __name__=='__main__':main()
