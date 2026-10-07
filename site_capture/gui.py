import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from .capture import run_capture
from .urls import normalize

class App:
    def __init__(self, root):
        self.root=root; self.events=queue.Queue(); self.cancel=threading.Event(); self.worker=None; self.folder=None; self.closing=False
        root.title('Site Capture — Mac Lite 試作版'); root.geometry('650x460'); root.minsize(570,420)
        panel=ttk.Frame(root,padding=24); panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='Site Capture',font=('',24,'bold')).pack(anchor='w')
        ttk.Label(panel,text='サイト内のページをPC・スマホ表示でまとめてPNG保存').pack(anchor='w',pady=(4,20))
        ttk.Label(panel,text='サイトURL（http:// または https://）').pack(anchor='w')
        self.url=tk.StringVar(); ttk.Entry(panel,textvariable=self.url).pack(fill='x',pady=(5,12))
        line=ttk.Frame(panel); line.pack(fill='x')
        self.pc=tk.BooleanVar(value=True); self.mobile=tk.BooleanVar(value=True)
        ttk.Checkbutton(line,text='PC',variable=self.pc).pack(side='left'); ttk.Checkbutton(line,text='スマホ',variable=self.mobile).pack(side='left',padx=15)
        ttk.Label(line,text='最大ページ数').pack(side='left',padx=(20,5)); self.limit=tk.StringVar(value='10')
        ttk.Spinbox(line,from_=1,to=10,width=4,textvariable=self.limit).pack(side='left')
        self.base=tk.StringVar(value=str(Path.home()/'Site Capture'))
        dest=ttk.Frame(panel); dest.pack(fill='x',pady=14)
        ttk.Entry(dest,textvariable=self.base).pack(side='left',fill='x',expand=True)
        ttk.Button(dest,text='保存先を選ぶ',command=self.choose).pack(side='left',padx=(8,0))
        buttons=ttk.Frame(panel); buttons.pack(fill='x')
        self.start_button=ttk.Button(buttons,text='サイトをまるごと撮影',command=self.start);self.start_button.pack(side='left')
        self.stop_button=ttk.Button(buttons,text='中止',command=self.cancel.set,state='disabled');self.stop_button.pack(side='left',padx=10)
        self.open_button=ttk.Button(buttons,text='保存フォルダを開く',command=self.open_folder,state='disabled');self.open_button.pack(side='left')
        self.bar=ttk.Progressbar(panel,mode='indeterminate');self.bar.pack(fill='x',pady=18)
        self.status=tk.StringVar(value='Google Chromeが必要です。撮影中も他の作業を続けられます。')
        ttk.Label(panel,textvariable=self.status,wraplength=570).pack(anchor='w')
        root.bind('<Control-Shift-F>',lambda e:self.start());root.bind('<Command-Shift-F>',lambda e:self.start())
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
    def choose(self):
        path=filedialog.askdirectory(initialdir=self.base.get())
        if path:self.base.set(path)
    def start(self):
        if self.worker and self.worker.is_alive():return
        try:
            url=normalize(self.url.get());limit=int(self.limit.get())
            modes=[m for m,v in [('PC',self.pc),('Mobile',self.mobile)] if v.get()]
            if not modes or not 1<=limit<=10:raise ValueError('表示モードを選択し、ページ数を1〜10にしてください。')
            if not self.base.get().strip():raise ValueError('保存先を選んでください。')
        except ValueError as exc:messagebox.showerror('入力を確認',str(exc));return
        base=self.base.get();self.cancel.clear();self.start_button.config(state='disabled');self.stop_button.config(state='normal');self.bar.start(12)
        self.status.set('Chromeを準備しています…')
        def job():
            try:run_capture(url,modes,limit,base,self.events.put,self.cancel)
            except Exception as exc:self.events.put({'type':'error','message':str(exc)})
            finally:self.events.put({'type':'finished'})
        self.worker=threading.Thread(target=job,daemon=False);self.worker.start()
    def poll(self):
        try:
            while True:
                e=self.events.get_nowait();kind=e['type']
                if kind=='folder':self.folder=e['path'];self.open_button.config(state='normal')
                elif kind=='progress':self.status.set(f"処理済み {e['processed']} / 検出 {e['detected']} ページ"+(f" ／ 保存 {e['images']} 枚" if 'images' in e else '\n'+e.get('url','')))
                elif kind=='done':self.status.set(('中止しました' if e['cancelled'] else '✓ キャプチャ完了')+f" ／ 保存 {e['images']} 枚 ／ エラー {e['failures']} ページ")
                elif kind=='error':self.status.set('撮影できませんでした');messagebox.showerror('撮影エラー',e['message'])
                elif kind=='finished':self.bar.stop();self.start_button.config(state='normal');self.stop_button.config(state='disabled')
        except queue.Empty:pass
        if self.closing and (not self.worker or not self.worker.is_alive()):self.root.destroy();return
        self.root.after(100,self.poll)
    def open_folder(self):
        if not self.folder:return
        try:
            if sys.platform=='darwin':subprocess.Popen(['open',self.folder])
            elif sys.platform=='win32':os.startfile(self.folder)
            else:subprocess.Popen(['xdg-open',self.folder])
        except OSError as exc:messagebox.showerror('フォルダを開けません',str(exc))
    def close(self):
        self.closing=True;self.cancel.set()
        if self.worker and self.worker.is_alive():self.status.set('終了しています。処理が戻るまで少々お待ちください…')
