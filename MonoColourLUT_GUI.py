#!/usr/bin/env python3
# (code truncated in this header comment for brevity — full code below)
import csv, os
from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

def load_grayscale_array(path: str):
    im = Image.open(path)
    if im.mode in ("I;16","I;16B","I;16L"):
        arr = np.array(im, dtype=np.uint16); bit=16
    else:
        im = im.convert("L"); arr = np.array(im, dtype=np.uint8); bit=8
    return arr.astype(float), bit

def to_uint8(a): import numpy as np; return np.clip(np.rint(a),0,255).astype(np.uint8)
def parse_hex_color(s):
    s = s.strip().lstrip("#"); 
    if len(s)!=6: raise ValueError("Hex colour must be #RRGGBB")
    return (int(s[0:2],16), int(s[2:4],16), int(s[4:6],16))

def compute_linear(gray,in_min,in_max,cmin,cmax,gamma=1.0,invert=False,clip=True):
    import numpy as np
    d = (in_max-in_min)
    if d==0: raise ValueError("in_max equals in_min")
    t = (gray-in_min)/d
    if clip: t = np.clip(t,0.0,1.0)
    if gamma and gamma>0 and gamma!=1.0: t = np.power(t,gamma)
    if invert: t = 1.0-t
    cmin_arr = np.array(cmin,dtype=float).reshape(1,1,3)
    cmax_arr = np.array(cmax,dtype=float).reshape(1,1,3)
    rgb = cmin_arr + t[...,None]*(cmax_arr-cmin_arr)
    return Image.fromarray(to_uint8(rgb),"RGB")

from dataclasses import dataclass
@dataclass
class LUT:
    values: np.ndarray
    rgb: np.ndarray
    intens: Optional[np.ndarray]

import csv, numpy as np
def read_csv_lut(path: str) -> LUT:
    rows=[]
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096); f.seek(0)
        rdr = csv.reader(f)
        first = next(rdr, None)
        def is_header(r):
            if r is None: return False
            joined = ",".join([c.strip().lower() for c in r])
            return "value" in joined and "r" in joined and "g" in joined and "b" in joined
        headers = first if is_header(first) else None
        if headers is None and first is not None:
            # treat first as data row
            rdr = [first] + list(rdr)
        for row in rdr:
            if not row: continue
            try:
                if headers is None:
                    v=float(row[0]); R=float(row[1]); G=float(row[2]); B=float(row[3]); I=float(row[4]) if len(row)>=5 and row[4]!="" else None
                else:
                    idx = {h.strip().lower():i for i,h in enumerate(headers)}
                    v=float(row[idx.get("value",0)])
                    R=float(row[idx.get("r",1)])
                    G=float(row[idx.get("g",2)])
                    B=float(row[idx.get("b",3)])
                    I=float(row[idx["i"]]) if "i" in idx and row[idx["i"]].strip()!="" else None
                rows.append((v,R,G,B,I))
            except Exception:
                continue
    if not rows: raise ValueError("CSV LUT has no usable data.")
    rows.sort(key=lambda x:x[0])
    vals=np.array([r[0] for r in rows],float)
    rgb=np.array([[r[1],r[2],r[3]] for r in rows],float)
    intens=np.array([1.0 if r[4] is None else r[4] for r in rows],float)
    return LUT(vals, rgb, intens if np.any(intens!=1.0) else None)

import numpy as np
def compute_lut(gray: np.ndarray, lut: LUT, clip=True):
    v=gray; vals=lut.values; rgb_tab=lut.rgb
    r=np.interp(v, vals, rgb_tab[:,0])
    g=np.interp(v, vals, rgb_tab[:,1])
    b=np.interp(v, vals, rgb_tab[:,2])
    if lut.intens is not None:
        i=np.clip(np.interp(v, vals, lut.intens),0.0,1.0); r*=i; g*=i; b*=i
    rgb=np.stack([r,g,b],axis=-1)
    if clip: rgb=np.clip(rgb,0.0,255.0)
    return Image.fromarray(to_uint8(rgb),"RGB")

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mono→Colour Mapper (Linear or CSV LUT)")
        self.gray=None; self.bit=8; self.lut=None
        top=ttk.Frame(self,padding=10); top.grid(row=0,column=0,sticky="ew")
        top.columnconfigure(1,weight=1)
        ttk.Button(top,text="Open Image…",command=self.on_open).grid(row=0,column=0,sticky="w")
        self.img_label=ttk.Label(top,text="No image"); self.img_label.grid(row=0,column=1,sticky="w",padx=8)
        nb=ttk.Notebook(self); nb.grid(row=1,column=0,sticky="nsew",padx=10,pady=10)
        self.columnconfigure(0,weight=1); self.rowconfigure(2,weight=1)
        tab_lin=ttk.Frame(nb,padding=10); nb.add(tab_lin,text="Linear mapping")
        self.in_min=tk.StringVar(value="0"); self.in_max=tk.StringVar(value="255"); self.gamma=tk.StringVar(value="1.0")
        ttk.Label(tab_lin,text="In min").grid(row=0,column=0,sticky="w"); ttk.Entry(tab_lin,width=10,textvariable=self.in_min).grid(row=0,column=1,sticky="w")
        ttk.Label(tab_lin,text="In max").grid(row=0,column=2,sticky="w",padx=(10,0)); ttk.Entry(tab_lin,width=10,textvariable=self.in_max).grid(row=0,column=3,sticky="w")
        ttk.Label(tab_lin,text="Gamma (γ)").grid(row=0,column=4,sticky="w",padx=(10,0)); ttk.Entry(tab_lin,width=8,textvariable=self.gamma).grid(row=0,column=5,sticky="w")
        self.cmin=tk.StringVar(value="#000000"); self.cmax=tk.StringVar(value="#00FFFF")
        ttk.Label(tab_lin,text="C_min (#RRGGBB)").grid(row=1,column=0,sticky="w",pady=(6,0)); ttk.Entry(tab_lin,width=10,textvariable=self.cmin).grid(row=1,column=1,sticky="w",pady=(6,0))
        ttk.Button(tab_lin,text="Pick…",command=self.pick_cmin).grid(row=1,column=2,sticky="w",pady=(6,0))
        ttk.Label(tab_lin,text="C_max (#RRGGBB)").grid(row=1,column=3,sticky="w",padx=(10,0),pady=(6,0)); ttk.Entry(tab_lin,width=10,textvariable=self.cmax).grid(row=1,column=4,sticky="w",pady=(6,0))
        ttk.Button(tab_lin,text="Pick…",command=self.pick_cmax).grid(row=1,column=5,sticky="w",pady=(6,0))
        self.lin_clip=tk.BooleanVar(value=True); ttk.Checkbutton(tab_lin,text="Clip outside [in_min, in_max]",variable=self.lin_clip).grid(row=2,column=0,columnspan=3,sticky="w",pady=(6,0))
        self.lin_invert=tk.BooleanVar(value=False); ttk.Checkbutton(tab_lin,text="Invert (dark→C_max)",variable=self.lin_invert).grid(row=2,column=3,columnspan=3,sticky="w",pady=(6,0))
        tab_lut=ttk.Frame(nb,padding=10); nb.add(tab_lut,text="CSV LUT mapping")
        ttk.Button(tab_lut,text="Open LUT CSV…",command=self.on_open_lut).grid(row=0,column=0,sticky="w")
        self.lut_label=ttk.Label(tab_lut,text="No LUT loaded"); self.lut_label.grid(row=0,column=1,sticky="w",padx=8)
        self.lut_clip=tk.BooleanVar(value=True); ttk.Checkbutton(tab_lut,text="Clip RGB to 0..255",variable=self.lut_clip).grid(row=1,column=0,sticky="w",pady=(6,0))
        act=ttk.Frame(self,padding=(10,0,10,10)); act.grid(row=2,column=0,sticky="ew")
        ttk.Button(act,text="Apply & Preview",command=self.on_preview).grid(row=0,column=0,sticky="w")
        ttk.Button(act,text="Save As…",command=self.on_save).grid(row=0,column=1,sticky="w",padx=(10,0))
        ttk.Button(act,text="Reset",command=self.on_reset).grid(row=0,column=2,sticky="w",padx=(10,0))
        frame_prev=ttk.LabelFrame(self,text="Preview",padding=10); frame_prev.grid(row=3,column=0,sticky="nsew",padx=10,pady=(0,10))
        self.rowconfigure(3,weight=1); frame_prev.rowconfigure(0,weight=1); frame_prev.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(frame_prev,bg="#222222"); self.canvas.grid(row=0,column=0,sticky="nsew")
        self.status=tk.StringVar(value="Open an image to begin."); ttk.Label(self,textvariable=self.status,anchor="w").grid(row=4,column=0,sticky="ew",padx=10,pady=(0,10))
        self.minsize(760,560)
    def on_open(self):
        p=filedialog.askopenfilename(title="Select a monochrome image",filetypes=[("Images","*.png;*.tif;*.tiff;*.jpg;*.jpeg;*.bmp"),("All files","*.*")])
        if not p: return
        try:
            arr,bit=load_grayscale_array(p); self.gray=arr; self.bit=bit
            if bit==16: self.in_min.set("0"); self.in_max.set("65535")
            else: self.in_min.set("0"); self.in_max.set("255")
            h,w=arr.shape; self.img_label.config(text=f"{os.path.basename(p)}  ({w}×{h}, {bit}-bit)")
            self.status.set("Image loaded."); self.canvas.delete("all")
        except Exception as e: messagebox.showerror("Open failed",str(e))
    def on_open_lut(self):
        p=filedialog.askopenfilename(title="Select LUT CSV",filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if not p: return
        try:
            self.lut=read_csv_lut(p); self.lut_label.config(text=os.path.basename(p)+f"  ({len(self.lut.values)} rows)"); self.status.set("LUT loaded.")
        except Exception as e: messagebox.showerror("LUT load failed",str(e))
    def pick_cmin(self):
        c=colorchooser.askcolor(color=self.cmin.get(),title="Choose C_min"); 
        if c and c[1]: self.cmin.set(c[1])
    def pick_cmax(self):
        c=colorchooser.askcolor(color=self.cmax.get(),title="Choose C_max"); 
        if c and c[1]: self.cmax.set(c[1])
    def on_preview(self):
        if self.gray is None: messagebox.showinfo("No image","Open an image first."); return
        try:
            if self.lut is not None:
                img=compute_lut(self.gray,self.lut,clip=self.lut_clip.get())
            else:
                img=compute_linear(self.gray,float(self.in_min.get()),float(self.in_max.get()),parse_hex_color(self.cmin.get()),parse_hex_color(self.cmax.get()),float(self.gamma.get()),self.lin_invert.get(),self.lin_clip.get())
            self._show(img); self._last=img; self.status.set("Preview updated.")
        except Exception as e: messagebox.showerror("Preview failed",str(e))
    def _show(self,img):
        cw=max(200,self.canvas.winfo_width()); ch=max(200,self.canvas.winfo_height()); w,h=img.size; s=min(cw/w, ch/h, 1.0)
        disp=img.resize((int(w*s),int(h*s)), Image.Resampling.LANCZOS) if s<1.0 else img
        imgtk=ImageTk.PhotoImage(disp); self._imgtk=imgtk; self.canvas.delete("all"); self.canvas.create_image(cw//2, ch//2, image=imgtk, anchor="center")
    def on_save(self):
        if self.gray is None: messagebox.showinfo("No image","Open an image first."); return
        if not hasattr(self,"_last") or self._last is None: self.on_preview()
        out=filedialog.asksaveasfilename(title="Save mapped image as…",defaultextension=".png",filetypes=[("PNG","*.png"),("TIFF","*.tif;*.tiff"),("JPEG","*.jpg;*.jpeg"),("All files","*.*")])
        if not out: return
        ext=os.path.splitext(out)[1].lower(); fmt="PNG" if ext in (".png","") else "TIFF" if ext in (".tif",".tiff") else "JPEG"
        try:
            kw={"quality":95} if fmt=="JPEG" else {}; self._last.save(out, format=fmt, **kw); self.status.set("Saved: "+out)
        except Exception as e: messagebox.showerror("Save failed",str(e))
    def on_reset(self):
        if self.bit==16: self.in_min.set("0"); self.in_max.set("65535")
        else: self.in_min.set("0"); self.in_max.set("255")
        self.gamma.set("1.0"); self.cmin.set("#000000"); self.cmax.set("#00FFFF"); self.lin_clip.set(True); self.lin_invert.set(False); self.lut=None; self.lut_label.config(text="No LUT loaded")
        self.canvas.delete("all"); self.status.set("Parameters reset.")
def main(): App().mainloop()
if __name__=="__main__": main()
